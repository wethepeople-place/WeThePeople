"""Sourced Discuss feed plus bounded authenticated safety actions."""

from datetime import datetime, timezone
from typing import Literal, Optional
from urllib.parse import parse_qs, urlparse
import re
import requests

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload, selectinload

from models.auth_models import User
from models.database import Bill, get_db
from models.social_models import (
    DiscussionAttachment,
    DiscussionBookmark,
    DiscussionBlock,
    DiscussionPost,
    DiscussionReaction,
    DiscussionReply,
    DiscussionReport,
    DiscussionVideoLink,
)
from models.issue_models import Issue, Video, VideoIssue
from routers.issues import _source
from routers.issues import list_issue_agenda
from routers.videos import _interaction_state as _video_interaction_state
from routers.videos import _query as _video_query
from routers.videos import _serialize as _serialize_video
from models.response_schemas import IssueSource
from services.jwt_auth import get_current_user, get_optional_user
from services.rate_limit_store import check_rate_limit
from services.social_link_classifier import confidence_for, fetch_social_metadata, rank_agenda_issues

router = APIRouter(prefix="/discussions", tags=["discussions"])

REPLY_LIMIT = 10
REPORT_LIMIT = 5
BLOCK_LIMIT = 10
POST_LIMIT = 5
ENGAGEMENT_LIMIT = 30
LINK_SUGGEST_LIMIT = 20
YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
TIKTOK_ID = re.compile(r"^[0-9]{10,25}$")
FACEBOOK_ID = re.compile(r"^[A-Za-z0-9_-]{5,100}$")
INSTAGRAM_ID = re.compile(r"^[A-Za-z0-9_-]{5,64}$")
DEMO_EMAIL_PREFIX = "demo.discussion."


class ReplyCreate(BaseModel):
    body: str = Field(min_length=1, max_length=10000)
    parent_reply_id: Optional[int] = None

    @field_validator("body")
    @classmethod
    def body_must_have_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Reply body must contain text")
        return value


class ReportCreate(BaseModel):
    target_type: Literal["post", "reply", "user"]
    target_id: int
    reason: str = Field(min_length=1, max_length=100)
    details: Optional[str] = Field(default=None, max_length=2000)


class DiscussionCreate(BaseModel):
    body: str = Field(default="", max_length=10000)
    video_url: Optional[str] = Field(default=None, min_length=1, max_length=1000)
    issue_slug: Optional[str] = Field(default=None, min_length=1, max_length=100)

    @field_validator("body")
    @classmethod
    def body_must_have_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            return ""
        return value


class LinkSuggestionRequest(BaseModel):
    video_url: str = Field(min_length=1, max_length=1000)


class LinkSuggestionItem(BaseModel):
    slug: str
    title: str
    score: int


class LinkSuggestionResponse(BaseModel):
    provider: Literal["youtube", "tiktok", "facebook", "instagram"]
    canonical_url: str
    suggested_issue: Optional[LinkSuggestionItem]
    alternatives: list[LinkSuggestionItem]
    confidence: Literal["low", "medium", "high"]
    metadata_available: bool


class VideoCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=10000)

    @field_validator("body")
    @classmethod
    def body_must_have_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Comment body must contain text")
        return value


class DiscussionVideoLinkItem(BaseModel):
    provider: Literal["youtube", "tiktok", "facebook", "instagram"]
    provider_video_id: str
    canonical_url: str


class DiscussionCreatedResponse(BaseModel):
    id: int
    moderation_status: Literal["pending", "published"]
    message: str


class DiscussionAuthor(BaseModel):
    id: Optional[int]
    display_name: str
    is_demo: bool = False


class DiscussionAttachmentItem(BaseModel):
    type: str
    reference_id: str
    label: Optional[str]
    source: Optional[IssueSource] = None


class DiscussionPostItem(BaseModel):
    id: int
    author: DiscussionAuthor
    body: str
    moderation_status: Literal["published"]
    reply_count: int
    created_at: str
    updated_at: str
    attachments: list[DiscussionAttachmentItem]
    video_link: Optional[DiscussionVideoLinkItem]
    reactions: dict[str, int]
    viewer_reactions: list[Literal["like", "insightful", "disagree"]]
    viewer_bookmarked: bool


class DiscussionFeedResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[DiscussionPostItem]


class DiscussionReplyItem(BaseModel):
    id: int
    parent_reply_id: Optional[int]
    author: DiscussionAuthor
    body: str
    moderation_status: Literal["published"]
    created_at: str
    updated_at: str


class DiscussionDetailResponse(DiscussionPostItem):
    replies: list[DiscussionReplyItem]
    reply_limit: int
    reply_offset: int
    reply_total: int


class ReplyCreatedResponse(BaseModel):
    id: int
    post_id: int
    moderation_status: Literal["published"]


class StatusResponse(BaseModel):
    status: str


class ReactionResponse(BaseModel):
    reaction: Literal["like", "insightful", "disagree"]
    enabled: bool
    reactions: dict[str, int]


class BookmarkResponse(BaseModel):
    bookmarked: bool


def _rate_limit(request: Request, user: User, endpoint: str, maximum: int, db: Session) -> None:
    host = request.client.host if request.client else "unknown"
    allowed, _, reset_at = check_rate_limit(
        ip=f"user:{user.id}:ip:{host}",
        endpoint=endpoint,
        max_requests=maximum,
        window_seconds=60,
        db=db,
    )
    if not allowed:
        retry_after = max(1, int(reset_at - datetime.now(timezone.utc).timestamp()))
        raise HTTPException(status_code=429, detail="Rate limit exceeded", headers={"Retry-After": str(retry_after)})


def _blocked_ids(user: Optional[User], db: Session) -> set[int]:
    if user is None:
        return set()
    rows = db.query(DiscussionBlock).filter(DiscussionBlock.blocker_id == user.id).all()
    return {row.blocked_id for row in rows}


def _attachment(row: DiscussionAttachment) -> dict:
    values = {
        "video": row.video_id,
        "issue": row.issue_slug,
        "bill": row.bill_id,
        "politician": row.politician_id,
        "solution": str(row.solution_id) if row.solution_id is not None else None,
        "source": str(row.source_id) if row.source_id is not None else None,
    }
    payload = {"type": row.attachment_type, "reference_id": values[row.attachment_type], "label": row.label}
    if row.attachment_type == "source":
        payload["source"] = _source(row.source)
    return payload


def _engagement(row: DiscussionPost, db: Session, user: Optional[User]) -> dict:
    counts = {"like": 0, "insightful": 0, "disagree": 0}
    for reaction, count in db.query(DiscussionReaction.reaction, func.count(DiscussionReaction.id)).filter_by(
        target_type="post", target_id=row.id
    ).group_by(DiscussionReaction.reaction).all():
        counts[reaction] = count
    viewer_reactions: list[str] = []
    viewer_bookmarked = False
    if user:
        viewer_reactions = [value for value, in db.query(DiscussionReaction.reaction).filter_by(
            user_id=user.id, target_type="post", target_id=row.id
        ).order_by(DiscussionReaction.reaction.asc()).all()]
        viewer_bookmarked = db.query(DiscussionBookmark.id).filter_by(user_id=user.id, post_id=row.id).first() is not None
    return {"reactions": counts, "viewer_reactions": viewer_reactions, "viewer_bookmarked": viewer_bookmarked}


def _post(row: DiscussionPost, published_reply_count: int, db: Session, user: Optional[User]) -> dict:
    is_demo = bool(row.author and row.author.email.startswith(DEMO_EMAIL_PREFIX))
    return {
        "id": row.id,
        "author": {"id": row.author_id, "display_name": row.author_label, "is_demo": is_demo},
        "body": row.body,
        "moderation_status": row.moderation_status,
        "reply_count": published_reply_count,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
        "attachments": [_attachment(item) for item in sorted(row.attachments, key=lambda item: item.attachment_type)],
        "video_link": ({
            "provider": row.video_link.provider,
            "provider_video_id": row.video_link.provider_video_id,
            "canonical_url": row.video_link.canonical_url,
        } if row.video_link else None),
        **_engagement(row, db, user),
    }


def _social_link(raw_url: str) -> tuple[str, str, str]:
    try:
        parsed = urlparse(raw_url.strip())
    except ValueError:
        raise HTTPException(status_code=422, detail="Enter a valid Facebook, TikTok, Instagram, or YouTube link")
    if parsed.scheme != "https":
        raise HTTPException(status_code=422, detail="Social links must use https")
    host = (parsed.hostname or "").lower()
    parts = [part for part in parsed.path.split("/") if part]
    video_id: Optional[str] = None
    if host == "youtu.be":
        video_id = parts[0] if len(parts) == 1 else None
    elif host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [None])[0]
        elif parsed.path.startswith(("/shorts/", "/embed/")):
            video_id = parts[1] if len(parts) == 2 else None
        if video_id and YOUTUBE_ID.fullmatch(video_id):
            return "youtube", video_id, f"https://www.youtube.com/watch?v={video_id}"
    elif host in {"tiktok.com", "www.tiktok.com", "m.tiktok.com"}:
        if len(parts) == 3 and parts[0].startswith("@") and parts[1] == "video":
            video_id = parts[2]
        if video_id and TIKTOK_ID.fullmatch(video_id):
            return "tiktok", video_id, f"https://www.tiktok.com/{parts[0]}/video/{video_id}"
    elif host in {"facebook.com", "www.facebook.com", "m.facebook.com", "web.facebook.com"}:
        query_id = parse_qs(parsed.query).get("v", [None])[0] if parsed.path in {"/watch", "/watch/"} else None
        if query_id and query_id.isdigit():
            video_id = query_id
            return "facebook", video_id, f"https://www.facebook.com/watch/?v={video_id}"
        for marker in ("videos", "reel", "posts"):
            if marker in parts and parts.index(marker) + 1 < len(parts):
                video_id = parts[parts.index(marker) + 1]
                break
        if video_id and FACEBOOK_ID.fullmatch(video_id):
            marker = next(marker for marker in ("videos", "reel", "posts") if marker in parts)
            prefix = parts[:parts.index(marker)]
            return "facebook", video_id, f"https://www.facebook.com/{'/'.join([*prefix, marker, video_id])}"
    elif host in {"instagram.com", "www.instagram.com"}:
        if len(parts) == 2 and parts[0] in {"p", "reel", "tv"}:
            video_id = parts[1]
        if video_id and INSTAGRAM_ID.fullmatch(video_id):
            return "instagram", video_id, f"https://www.instagram.com/{parts[0]}/{video_id}/"
    raise HTTPException(status_code=422, detail="Enter a direct Facebook, TikTok, Instagram, or YouTube post link")


def _base_query(db: Session):
    return db.query(DiscussionPost).options(
        joinedload(DiscussionPost.author),
        selectinload(DiscussionPost.attachments).joinedload(DiscussionAttachment.source),
        joinedload(DiscussionPost.video_link),
    ).filter(DiscussionPost.moderation_status == "published")


def _issue_suggestions(provider: str, canonical_url: str, db: Session, extra_text: str = "") -> tuple[list[LinkSuggestionItem], str, bool]:
    metadata = ""
    try:
        metadata = fetch_social_metadata(provider, canonical_url)
    except (requests.RequestException, ValueError):
        metadata = ""
    issues = {row.slug: row.title for row in db.query(Issue).order_by(Issue.slug.asc()).all()}
    matches = rank_agenda_issues(f"{metadata} {extra_text}", issues)
    ranked = [LinkSuggestionItem(slug=item.slug, title=issues[item.slug], score=item.score) for item in matches[:3]]
    return ranked, confidence_for(matches), bool(metadata.strip())


@router.post("/link-suggestion", response_model=LinkSuggestionResponse)
def suggest_discussion_issue(
    body: LinkSuggestionRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _rate_limit(request, user, "discussions:link-suggestion", LINK_SUGGEST_LIMIT, db)
    provider, _, canonical_url = _social_link(body.video_url)
    ranked, confidence, metadata_available = _issue_suggestions(provider, canonical_url, db)
    return {
        "provider": provider,
        "canonical_url": canonical_url,
        "suggested_issue": ranked[0] if ranked else None,
        "alternatives": ranked[1:],
        "confidence": confidence,
        "metadata_available": metadata_available,
    }


@router.post("", status_code=status.HTTP_201_CREATED, response_model=DiscussionCreatedResponse)
def create_discussion(
    body: DiscussionCreate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _rate_limit(request, user, "discussions:create", POST_LIMIT, db)
    video_link = _social_link(body.video_url) if body.video_url else None
    if not video_link and not body.body:
        raise HTTPException(status_code=422, detail="Add a thought or paste a supported social link")
    issue_slug = body.issue_slug
    if video_link and not issue_slug:
        suggestions, _, _ = _issue_suggestions(video_link[0], video_link[2], db, body.body)
        issue_slug = suggestions[0].slug if suggestions else None
        if not issue_slug:
            raise HTTPException(status_code=422, detail="We could not match this link yet. Add a few words about its topic and try again")
    issue_record = db.get(Issue, issue_slug) if issue_slug else None
    if issue_slug and issue_record is None:
        raise HTTPException(status_code=422, detail="Choose a reviewed WTP issue")
    post = DiscussionPost(
        author_id=user.id,
        author_label=user.display_name or "Community member",
        body=body.body or f"Shared a {video_link[0].title()} video.",
        moderation_status="published",
    )
    if video_link:
        provider, video_id, canonical_url = video_link
        post.video_link = DiscussionVideoLink(
            provider=provider, provider_video_id=video_id, canonical_url=canonical_url
        )
    if issue_slug:
        post.attachments.append(DiscussionAttachment(
            attachment_type="issue", issue_slug=issue_slug, label=issue_record.title
        ))
    db.add(post)
    db.commit()
    db.refresh(post)
    return {"id": post.id, "moderation_status": "published", "message": "Posted"}


@router.get("", response_model=DiscussionFeedResponse)
def list_discussions(
    issue_slug: Optional[str] = Query(default=None, min_length=1, max_length=100),
    video_id: Optional[str] = Query(default=None, min_length=1, max_length=100),
    content: Literal["all", "discussions", "proposals", "videos"] = Query(default="all"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    blocked = _blocked_ids(user, db)
    query = _base_query(db)
    if issue_slug:
        query = query.filter(DiscussionPost.attachments.any(DiscussionAttachment.issue_slug == issue_slug))
    if video_id:
        query = query.filter(DiscussionPost.attachments.any(
            (DiscussionAttachment.attachment_type == "video") & (DiscussionAttachment.video_id == video_id)
        ))
    if content == "discussions":
        query = query.filter(~DiscussionPost.video_link.has()).filter(~DiscussionPost.attachments.any(
            DiscussionAttachment.attachment_type.in_(("solution", "video"))
        ))
    elif content == "proposals":
        query = query.filter(DiscussionPost.attachments.any(
            DiscussionAttachment.attachment_type == "solution"
        ))
    elif content == "videos":
        query = query.filter(DiscussionPost.video_link.has())
    if blocked:
        query = query.filter((DiscussionPost.author_id.is_(None)) | (~DiscussionPost.author_id.in_(blocked)))
    total = query.count()
    rows = query.order_by(DiscussionPost.created_at.desc(), DiscussionPost.id.desc()).offset(offset).limit(limit).all()
    items = []
    for row in rows:
        reply_count = db.query(DiscussionReply).filter_by(post_id=row.id, moderation_status="published").filter(
            (DiscussionReply.author_id.notin_(blocked)) if blocked else True
        ).count()
        items.append(_post(row, reply_count, db, user))
    return {"total": total, "limit": limit, "offset": offset, "items": items}


@router.get("/videos/{video_id}", response_model=DiscussionFeedResponse)
def list_video_comments(
    video_id: str,
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Return the canonical public conversation attached to one Watch video."""
    community_match = re.fullmatch(r"community-(\d+)", video_id)
    if community_match:
        post_id = int(community_match.group(1))
        blocked = _blocked_ids(user, db)
        row = _base_query(db).join(DiscussionVideoLink).filter(
            DiscussionPost.id == post_id,
            DiscussionPost.moderation_status == "published",
        ).first()
        if row is None or (row.author_id is not None and row.author_id in blocked):
            raise HTTPException(status_code=404, detail="Video not found")
        reply_count = db.query(DiscussionReply).filter_by(post_id=row.id, moderation_status="published").filter(
            (DiscussionReply.author_id.notin_(blocked)) if blocked else True
        ).count()
        return {"total": 1, "limit": limit, "offset": offset, "items": [] if offset else [_post(row, reply_count, db, user)]}
    if db.get(Video, video_id) is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return list_discussions(
        issue_slug=None,
        video_id=video_id,
        content="all",
        limit=limit,
        offset=offset,
        user=user,
        db=db,
    )


@router.get("/continuation")
def list_discussion_continuation(
    bill_offset: int = Query(0, ge=0),
    bill_limit: int = Query(10, ge=1, le=25),
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Continue Discuss with real reviewed material, never duplicate community posts."""
    reviewed_rows = _video_query(db).order_by(
        Video.sort_order.asc(), Video.published_at.desc(), Video.video_id.asc()
    ).all()
    reviewed_videos = [
        {**_serialize_video(row, _video_interaction_state(db, row, user)), "content_origin": "reviewed"}
        for row in reviewed_rows
    ]
    agenda = list_issue_agenda(db)
    bill_query = db.query(Bill).order_by(Bill.latest_action_date.desc(), Bill.bill_id.asc())
    bill_total = bill_query.count()
    bills = bill_query.offset(bill_offset).limit(bill_limit).all()
    return {
        "reviewed_videos": reviewed_videos,
        "agenda": agenda["items"],
        "bills": [{
            "bill_id": row.bill_id,
            "title": row.title,
            "latest_action_text": row.latest_action_text,
            "latest_action_date": row.latest_action_date.isoformat() if row.latest_action_date else None,
        } for row in bills],
        "bill_total": bill_total,
        "bill_offset": bill_offset,
        "bill_limit": bill_limit,
    }


@router.post(
    "/videos/{video_id}/comments",
    status_code=status.HTTP_201_CREATED,
    response_model=DiscussionCreatedResponse,
)
def create_video_comment(
    video_id: str,
    body: VideoCommentCreate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Attach a moderated comment to one reviewed or community video identity."""
    _rate_limit(request, user, "discussions:video-comment", POST_LIMIT, db)
    community_match = re.fullmatch(r"community-(\d+)", video_id)
    if community_match:
        post_id = int(community_match.group(1))
        post = db.query(DiscussionPost).join(DiscussionVideoLink).filter(
            DiscussionPost.id == post_id,
            DiscussionPost.moderation_status == "published",
        ).first()
        if post is None:
            raise HTTPException(status_code=404, detail="Video not found")
        reply = DiscussionReply(
            post_id=post.id,
            author_id=user.id,
            body=body.body,
            moderation_status="pending",
        )
        db.add(reply)
        db.commit()
        db.refresh(reply)
        return {"id": reply.id, "moderation_status": "pending", "message": "Submitted for moderation"}
    if db.get(Video, video_id) is None:
        raise HTTPException(status_code=404, detail="Video not found")
    issue_slugs = [issue_slug for issue_slug, in db.query(VideoIssue.issue_slug).filter_by(video_id=video_id).all()]
    post = DiscussionPost(
        author_id=user.id,
        author_label=user.display_name or "Community member",
        body=body.body,
        moderation_status="pending",
    )
    post.attachments.append(DiscussionAttachment(
        attachment_type="video", video_id=video_id, label="Watch discussion"
    ))
    for issue_slug in sorted(issue_slugs):
        post.attachments.append(DiscussionAttachment(
            attachment_type="issue", issue_slug=issue_slug, label="Related issue"
        ))
    db.add(post)
    db.commit()
    db.refresh(post)
    return {"id": post.id, "moderation_status": "pending", "message": "Submitted for moderation"}


@router.get("/{post_id}", response_model=DiscussionDetailResponse)
def get_discussion(
    post_id: int,
    reply_limit: int = Query(50, ge=1, le=100),
    reply_offset: int = Query(0, ge=0),
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    blocked = _blocked_ids(user, db)
    row = _base_query(db).filter(DiscussionPost.id == post_id).first()
    if row is None or (row.author_id is not None and row.author_id in blocked):
        raise HTTPException(status_code=404, detail="Discussion not found")
    replies_query = db.query(DiscussionReply).options(joinedload(DiscussionReply.author)).filter_by(
        post_id=post_id, moderation_status="published"
    )
    if blocked:
        replies_query = replies_query.filter(~DiscussionReply.author_id.in_(blocked))
    total = replies_query.count()
    replies = replies_query.order_by(DiscussionReply.created_at.asc(), DiscussionReply.id.asc()).offset(reply_offset).limit(reply_limit).all()
    return {
        **_post(row, total, db, user),
        "replies": [{
            "id": reply.id,
            "parent_reply_id": reply.parent_reply_id,
            "author": {
                "id": reply.author_id,
                "display_name": reply.author.display_name or "Community member",
                "is_demo": reply.author.email.startswith(DEMO_EMAIL_PREFIX),
            },
            "body": reply.body,
            "moderation_status": reply.moderation_status,
            "created_at": reply.created_at.isoformat(),
            "updated_at": reply.updated_at.isoformat(),
        } for reply in replies],
        "reply_limit": reply_limit,
        "reply_offset": reply_offset,
        "reply_total": total,
    }


@router.post("/{post_id}/replies", status_code=status.HTTP_201_CREATED, response_model=ReplyCreatedResponse)
def create_reply(
    post_id: int,
    body: ReplyCreate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _rate_limit(request, user, "discussions:reply", REPLY_LIMIT, db)
    post = db.query(DiscussionPost).filter_by(id=post_id, moderation_status="published").first()
    if post is None:
        raise HTTPException(status_code=404, detail="Discussion not found")
    if post.author_id is not None and db.query(DiscussionBlock).filter_by(blocker_id=post.author_id, blocked_id=user.id).first():
        raise HTTPException(status_code=403, detail="Reply is not permitted")
    if body.parent_reply_id is not None:
        parent = db.query(DiscussionReply).filter_by(id=body.parent_reply_id, post_id=post_id, moderation_status="published").first()
        if parent is None:
            raise HTTPException(status_code=400, detail="Parent reply is invalid")
    reply = DiscussionReply(
        post_id=post_id,
        parent_reply_id=body.parent_reply_id,
        author_id=user.id,
        body=body.body.strip(),
        moderation_status="published",
    )
    db.add(reply)
    post.reply_count = db.query(DiscussionReply).filter_by(post_id=post_id, moderation_status="published").count() + 1
    db.commit()
    db.refresh(reply)
    return {"id": reply.id, "post_id": post_id, "moderation_status": reply.moderation_status}


def _actionable_post(post_id: int, user: User, db: Session) -> DiscussionPost:
    post = db.query(DiscussionPost).filter_by(id=post_id, moderation_status="published").first()
    if post is None:
        raise HTTPException(status_code=404, detail="Discussion not found")
    if post.author_id is not None and db.query(DiscussionBlock).filter_by(blocker_id=post.author_id, blocked_id=user.id).first():
        raise HTTPException(status_code=403, detail="This action is not permitted")
    return post


@router.put("/{post_id}/reactions/{reaction}", response_model=ReactionResponse)
def add_reaction(
    post_id: int,
    reaction: Literal["like", "insightful", "disagree"],
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _rate_limit(request, user, "discussions:engagement", ENGAGEMENT_LIMIT, db)
    post = _actionable_post(post_id, user, db)
    row = db.query(DiscussionReaction).filter_by(
        user_id=user.id, target_type="post", target_id=post_id, reaction=reaction
    ).first()
    if row is None:
        db.add(DiscussionReaction(user_id=user.id, target_type="post", target_id=post_id, reaction=reaction))
        db.commit()
    return {"reaction": reaction, "enabled": True, "reactions": _engagement(post, db, user)["reactions"]}


@router.delete("/{post_id}/reactions/{reaction}", response_model=ReactionResponse)
def remove_reaction(
    post_id: int,
    reaction: Literal["like", "insightful", "disagree"],
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _rate_limit(request, user, "discussions:engagement", ENGAGEMENT_LIMIT, db)
    post = _actionable_post(post_id, user, db)
    row = db.query(DiscussionReaction).filter_by(
        user_id=user.id, target_type="post", target_id=post_id, reaction=reaction
    ).first()
    if row:
        db.delete(row)
        db.commit()
    return {"reaction": reaction, "enabled": False, "reactions": _engagement(post, db, user)["reactions"]}


@router.put("/{post_id}/bookmark", response_model=BookmarkResponse)
def add_bookmark(
    post_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _rate_limit(request, user, "discussions:engagement", ENGAGEMENT_LIMIT, db)
    _actionable_post(post_id, user, db)
    if db.query(DiscussionBookmark).filter_by(user_id=user.id, post_id=post_id).first() is None:
        db.add(DiscussionBookmark(user_id=user.id, post_id=post_id))
        db.commit()
    return {"bookmarked": True}


@router.delete("/{post_id}/bookmark", response_model=BookmarkResponse)
def remove_bookmark(
    post_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _rate_limit(request, user, "discussions:engagement", ENGAGEMENT_LIMIT, db)
    _actionable_post(post_id, user, db)
    row = db.query(DiscussionBookmark).filter_by(user_id=user.id, post_id=post_id).first()
    if row:
        db.delete(row)
        db.commit()
    return {"bookmarked": False}


@router.post("/reports", status_code=status.HTTP_201_CREATED, response_model=StatusResponse)
def create_report(
    body: ReportCreate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _rate_limit(request, user, "discussions:report", REPORT_LIMIT, db)
    target_exists = {
        "post": db.get(DiscussionPost, body.target_id),
        "reply": db.get(DiscussionReply, body.target_id),
        "user": db.get(User, body.target_id),
    }[body.target_type]
    if target_exists is None:
        raise HTTPException(status_code=404, detail="Report target not found")
    report = DiscussionReport(
        reporter_id=user.id,
        target_type=body.target_type,
        target_id=body.target_id,
        reason=body.reason,
        details=body.details,
    )
    db.add(report)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Target already reported")
    return {"status": "received"}


@router.post("/blocks/{blocked_user_id}", status_code=status.HTTP_201_CREATED, response_model=StatusResponse)
def block_user(
    blocked_user_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _rate_limit(request, user, "discussions:block", BLOCK_LIMIT, db)
    if blocked_user_id == user.id:
        raise HTTPException(status_code=400, detail="You cannot block yourself")
    if db.get(User, blocked_user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    row = db.query(DiscussionBlock).filter_by(blocker_id=user.id, blocked_id=blocked_user_id).first()
    if row is None:
        db.add(DiscussionBlock(blocker_id=user.id, blocked_id=blocked_user_id))
        db.commit()
    return {"status": "blocked"}
