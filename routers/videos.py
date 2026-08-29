"""Public, read-only Watch video endpoints."""

import base64
import hashlib
import hmac
import json
import os
import re
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import and_, or_
import requests
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session, joinedload, selectinload

from models.database import get_db
from models.auth_models import User
from models.issue_models import Issue, Video, VideoBill, VideoIssue, VideoLike, VideoSave
from models.response_schemas import VideoInteractionState, VideoInteractionUpdate, VideoItem, VideoSharePreview, VideosResponse
from models.social_models import DiscussionAttachment, DiscussionBookmark, DiscussionPost, DiscussionReaction, DiscussionReply, DiscussionVideoLink
from routers.issues import _source
from services.watch_phase4c_production_media import production_metadata
from services.jwt_auth import get_current_user, get_optional_user
from services.rate_limit_store import check_rate_limit

router = APIRouter(prefix="/videos", tags=["videos"])
PUBLIC_WEB_ORIGIN = os.getenv("WTP_PUBLIC_WEB_ORIGIN", "https://app.wethepeople.place").rstrip("/")
CURSOR_SECRET = os.getenv("WTP_VIDEO_CURSOR_SECRET", "development-only-watch-cursor").encode()
WATCH_FIXTURE_PATH = Path(__file__).resolve().parents[1] / "data" / "watch_housing_rent.json"
COMMUNITY_VIDEO_ID = re.compile(r"^community-([1-9][0-9]*)$")
PROVIDER_LABELS = {"youtube": "YouTube", "tiktok": "TikTok", "facebook": "Facebook", "instagram": "Instagram"}


def _fixture_metadata(video_id: str) -> tuple[dict | None, dict | None]:
    """Return metadata only through the explicit development or production gate."""
    if os.getenv("WTP_ENV") == "production":
        return production_metadata(video_id, embed_enabled=os.getenv("WTP_ENABLE_PRODUCTION_WATCH_EMBED") == "true")
    if os.getenv("WTP_ENV") != "development" or os.getenv("WTP_ENABLE_DEVELOPMENT_WATCH_EMBED") != "true":
        return None, None
    try:
        payload = json.loads(WATCH_FIXTURE_PATH.read_text(encoding="utf-8"))
        record = next(item for item in payload.get("videos", ()) if item.get("video_id") == video_id)
        return record.get("delivery"), record.get("accessibility")
    except (OSError, ValueError, StopIteration, TypeError):
        return None, None


def _fixture_delivery(video_id: str) -> dict | None:
    """Return optional delivery metadata without adding it to the database schema."""
    delivery, _ = _fixture_metadata(video_id)
    try:
        if not isinstance(delivery, dict):
            return None
        canonical_url = delivery.get("canonical_url")
        poster_url = delivery.get("poster_url")
        mode = delivery.get("mode")
        if mode not in {"official_embed", "hosted_video", "link_out"} or not isinstance(canonical_url, str) or not canonical_url.startswith("https://"):
            return None
        if mode == "official_embed" and not all(delivery.get(field) for field in ("provider", "provider_video_id", "source_label")):
            return {"mode": "link_out", "canonical_url": canonical_url, "development_only": bool(delivery.get("development_only"))}
        if poster_url is not None and (
            not isinstance(poster_url, str)
            or not poster_url.startswith("/watch-thumbnails/")
            or not poster_url.endswith((".jpg", ".webp"))
            or ".." in poster_url
        ):
            delivery = {key: value for key, value in delivery.items() if key != "poster_url"}
        return delivery
    except (OSError, ValueError, StopIteration, TypeError):
        return None


def _fixture_accessibility(video_id: str) -> dict | None:
    """Return environment-authorized accessibility metadata from the fixture."""
    _, accessibility = _fixture_metadata(video_id)
    try:
        if not isinstance(accessibility, dict):
            return None
        transcript_url = accessibility.get("official_transcript_url")
        if accessibility.get("text_kind") not in {"overview", "transcript"} or not isinstance(transcript_url, str) or not transcript_url.startswith("https://") or not accessibility.get("official_transcript_label"):
            return None
        return accessibility
    except (OSError, ValueError, StopIteration, TypeError):
        return None


def _cursor(offset: int) -> str:
    payload = json.dumps({"v": 2, "o": offset}, separators=(",", ":"), sort_keys=True).encode()
    signature = hmac.new(CURSOR_SECRET, payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(payload + signature).decode().rstrip("=")


def _decode_cursor(value: str) -> int:
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        payload, signature = raw[:-32], raw[-32:]
        if not hmac.compare_digest(signature, hmac.new(CURSOR_SECRET, payload, hashlib.sha256).digest()):
            raise ValueError
        data = json.loads(payload)
        if data.get("v") != 2:
            raise ValueError
        offset = int(data["o"])
        if offset < 0:
            raise ValueError
        return offset
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise HTTPException(status_code=400, detail="Invalid video cursor") from None


def _share_preview(row: Video) -> dict:
    item = _serialize(row)
    return {
        "video_id": row.video_id,
        "content_origin": "reviewed",
        "content_origin": "reviewed",
        "canonical_url": f"{PUBLIC_WEB_ORIGIN}/watch/{quote(row.video_id, safe='')}",
        "title": f"{row.caption} | WeThePeople.place",
        "description": f"{row.creator_label} · {item['issue']['title']} · Source: {item['source']['publisher']}",
        "image_url": f"{PUBLIC_WEB_ORIGIN}/og-image.png",
        "source": item["source"],
    }


def _query(db: Session):
    return db.query(Video).options(
        joinedload(Video.source),
        selectinload(Video.issue_links).joinedload(VideoIssue.issue),
        selectinload(Video.bill_links).joinedload(VideoBill.bill),
    )


def _discussion_post_ids(db: Session, row: Video) -> list[int]:
    direct = db.query(DiscussionAttachment.post_id).join(DiscussionPost).filter(
        DiscussionAttachment.attachment_type == "video",
        DiscussionAttachment.video_id == row.video_id,
        DiscussionPost.moderation_status == "published",
    ).order_by(DiscussionAttachment.post_id).all()
    return [post_id for post_id, in direct]


def _interaction_state(db: Session, row: Video, user: User | None) -> dict:
    post_ids = _discussion_post_ids(db, row)
    reply_count = db.query(DiscussionReply).filter(
        DiscussionReply.post_id.in_(post_ids), DiscussionReply.moderation_status == "published"
    ).count() if post_ids else 0
    return {
        "discussion_post_id": post_ids[0] if post_ids else None,
        "discussion_count": len(post_ids) + reply_count,
        "like_count": db.query(VideoLike).filter(VideoLike.video_id == row.video_id).count(),
        "liked": bool(user and db.query(VideoLike.id).filter_by(video_id=row.video_id, user_id=user.id).first()),
        "saved": bool(user and db.query(VideoSave.id).filter_by(video_id=row.video_id, user_id=user.id).first()),
    }


def _serialize(row: Video, interaction: dict | None = None) -> dict:
    if len(row.issue_links) != 1 or row.issue_links[0].issue is None:
        raise HTTPException(status_code=503, detail="Video issue metadata is incomplete")
    issue = row.issue_links[0].issue
    bills = sorted(
        (link.bill for link in row.bill_links if link.bill is not None),
        key=lambda bill: bill.bill_id,
    )
    return {
        "video_id": row.video_id,
        "creator_label": row.creator_label,
        "caption": row.caption,
        "transcript": row.transcript,
        "captions_url": row.captions_url,
        "media_url": row.media_url,
        "delivery": _fixture_delivery(row.video_id),
        "accessibility": _fixture_accessibility(row.video_id),
        "published_at": row.published_at.isoformat(),
        "source": _source(row.source),
        "issue": {"slug": issue.slug, "title": issue.title},
        "bills": [{"bill_id": bill.bill_id, "title": bill.title} for bill in bills],
        **(interaction or {"discussion_post_id": None, "discussion_count": 0, "like_count": 0, "liked": False, "saved": False}),
    }


def _community_query(db: Session):
    return (
        db.query(DiscussionPost, DiscussionVideoLink, DiscussionAttachment, Issue)
        .join(DiscussionVideoLink, DiscussionVideoLink.post_id == DiscussionPost.id)
        .join(
            DiscussionAttachment,
            and_(
                DiscussionAttachment.post_id == DiscussionPost.id,
                DiscussionAttachment.attachment_type == "issue",
            ),
        )
        .join(Issue, Issue.slug == DiscussionAttachment.issue_slug)
        .filter(DiscussionPost.moderation_status == "published")
    )


def _community_row(db: Session, post_id: int):
    return _community_query(db).filter(DiscussionPost.id == post_id).first()


def _community_caption(post: DiscussionPost, provider_label: str, issue: Issue) -> str:
    neutral = re.fullmatch(r"Shared a [A-Za-z]+ video\.", post.body.strip())
    return f"{provider_label} video about {issue.title}" if neutral else post.body.strip()


def _serialize_community(db: Session, row, user: User | None = None) -> dict:
    post, video_link, _, issue = row
    provider_label = PROVIDER_LABELS[video_link.provider]
    video_id = f"community-{post.id}"
    reply_count = db.query(DiscussionReply).filter_by(post_id=post.id, moderation_status="published").count()
    delivery_mode = "official_embed" if video_link.provider in {"youtube", "tiktok", "facebook"} else "link_out"
    poster_url = f"/videos/community/{post.id}/poster" if video_link.provider == "youtube" else None
    return {
        "video_id": video_id,
        "content_origin": "community",
        "creator_label": post.author_label,
        "caption": _community_caption(post, provider_label, issue),
        "transcript": None,
        "captions_url": None,
        "media_url": video_link.canonical_url,
        "delivery": {
            "mode": delivery_mode,
            "provider": video_link.provider,
            "provider_video_id": video_link.provider_video_id,
            "canonical_url": video_link.canonical_url,
            "poster_url": poster_url,
            "source_label": provider_label,
            "development_only": False,
        },
        "accessibility": None,
        "published_at": post.created_at.isoformat(),
        "source": {
            "url": video_link.canonical_url,
            "publisher": provider_label,
            "retrieved_at": video_link.created_at.isoformat(),
        },
        "issue": {"slug": issue.slug, "title": issue.title},
        "bills": [],
        "discussion_post_id": post.id,
        "discussion_count": 1 + reply_count,
        "like_count": db.query(DiscussionReaction).filter_by(target_type="post", target_id=post.id, reaction="like").count(),
        "liked": bool(user and db.query(DiscussionReaction.id).filter_by(user_id=user.id, target_type="post", target_id=post.id, reaction="like").first()),
        "saved": bool(user and db.query(DiscussionBookmark.id).filter_by(user_id=user.id, post_id=post.id).first()),
    }


@router.get("", response_model=VideosResponse)
def list_videos(
    cursor: str | None = None,
    limit: int = Query(25, ge=1, le=100),
    issue_slug: str | None = Query(None, min_length=1, max_length=100),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    offset = _decode_cursor(cursor) if cursor else 0
    community_query = _community_query(db)
    reviewed_query = _query(db)
    if issue_slug:
        # Both community and reviewed videos already carry a canonical Issue
        # relationship. Filter on that stored identity; never reclassify or
        # guess from captions while serving an Issue Hub.
        community_query = community_query.filter(DiscussionAttachment.issue_slug == issue_slug)
        reviewed_query = reviewed_query.join(VideoIssue).filter(VideoIssue.issue_slug == issue_slug)
    # Community shares form the live, newest-first feed. The small reviewed
    # catalog follows in its editorial order, preserving its existing contract.
    community = [
        ("community", row)
        for row in community_query.order_by(DiscussionPost.created_at.desc(), DiscussionPost.id.desc()).all()
    ]
    reviewed = [
        ("reviewed", row)
        for row in reviewed_query.order_by(Video.sort_order.asc(), Video.published_at.desc(), Video.video_id.asc()).all()
    ]
    ordered = [*community, *reviewed]
    page = ordered[offset:offset + limit]
    videos = [
        _serialize_community(db, value, user) if origin == "community" else _serialize(value, _interaction_state(db, value, user))
        for origin, value in page
    ]
    next_offset = offset + len(page)
    has_more = next_offset < len(ordered)
    return {"total": len(ordered), "videos": videos, "next_cursor": _cursor(next_offset) if has_more else None, "has_more": has_more}


@router.get("/saved", response_model=VideosResponse)
def list_saved_videos(limit: int = Query(25, ge=1, le=25), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return only the authenticated viewer's private saved-video collection."""
    community_bookmarks = (
        db.query(DiscussionBookmark)
        .join(DiscussionPost, DiscussionPost.id == DiscussionBookmark.post_id)
        .join(DiscussionVideoLink, DiscussionVideoLink.post_id == DiscussionPost.id)
        .filter(DiscussionBookmark.user_id == user.id, DiscussionPost.moderation_status == "published")
        .order_by(DiscussionBookmark.created_at.desc(), DiscussionBookmark.id.desc())
        .limit(limit)
        .all()
    )
    community_rows = [row for bookmark in community_bookmarks if (row := _community_row(db, bookmark.post_id)) is not None]
    reviewed_total = db.query(VideoSave).filter(VideoSave.user_id == user.id).count()
    reviewed_rows = (
        _query(db)
        .join(VideoSave, VideoSave.video_id == Video.video_id)
        .filter(VideoSave.user_id == user.id)
        .order_by(VideoSave.created_at.desc(), Video.video_id.asc())
        .limit(max(0, limit - len(community_rows)))
        .all()
    )
    videos = [*[_serialize_community(db, row, user) for row in community_rows], *[_serialize(row, _interaction_state(db, row, user)) for row in reviewed_rows]]
    total = len(community_rows) + reviewed_total
    return {
        "total": total,
        "videos": videos,
        "next_cursor": None,
        "has_more": total > len(videos),
    }


@router.get("/{video_id}", response_model=VideoItem)
def get_video(video_id: str, user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    community_match = COMMUNITY_VIDEO_ID.fullmatch(video_id)
    if community_match:
        community = _community_row(db, int(community_match.group(1)))
        if community is None:
            raise HTTPException(status_code=404, detail="Video not found")
        return _serialize_community(db, community, user)
    row = _query(db).filter(Video.video_id == video_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return _serialize(row, _interaction_state(db, row, user))


@router.get("/community/{post_id}/poster", include_in_schema=False)
def get_community_video_poster(post_id: int, db: Session = Depends(get_db)):
    row = _community_row(db, post_id)
    if row is None or row[1].provider != "youtube":
        raise HTTPException(status_code=404, detail="Video poster not found")
    provider_video_id = row[1].provider_video_id
    try:
        response = requests.get(
            f"https://i.ytimg.com/vi/{provider_video_id}/hqdefault.jpg",
            headers={"User-Agent": "WeThePeople-WatchPoster/1.0 (+https://app.wethepeople.place)"},
            timeout=(2, 5),
            allow_redirects=False,
        )
        response.raise_for_status()
        if len(response.content) > 1_500_000:
            raise ValueError
    except (requests.RequestException, ValueError):
        raise HTTPException(status_code=404, detail="Video poster unavailable") from None
    return Response(
        content=response.content,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400, stale-while-revalidate=604800"},
    )


def _set_interaction(video_id: str, active: bool, model, request: Request, user: User, db: Session) -> dict:
    community_match = COMMUNITY_VIDEO_ID.fullmatch(video_id)
    if community_match:
        post_id = int(community_match.group(1))
        community = _community_row(db, post_id)
        if community is None:
            raise HTTPException(status_code=404, detail="Video not found")
        host = request.client.host if request.client else "unknown"
        allowed, _, reset_at = check_rate_limit(ip=f"user:{user.id}:ip:{host}", endpoint="watch:interaction", max_requests=60, window_seconds=60, db=db)
        if not allowed:
            retry_after = max(1, int(reset_at - datetime.now(timezone.utc).timestamp()))
            raise HTTPException(status_code=429, detail="Rate limit exceeded", headers={"Retry-After": str(retry_after)})
        if model is VideoLike:
            existing = db.query(DiscussionReaction).filter_by(user_id=user.id, target_type="post", target_id=post_id, reaction="like").first()
            if existing and not active: db.delete(existing)
            elif not existing and active: db.add(DiscussionReaction(user_id=user.id, target_type="post", target_id=post_id, reaction="like"))
        else:
            existing = db.query(DiscussionBookmark).filter_by(user_id=user.id, post_id=post_id).first()
            if existing and not active: db.delete(existing)
            elif not existing and active: db.add(DiscussionBookmark(user_id=user.id, post_id=post_id))
        db.commit()
        state = _serialize_community(db, community, user)
        return {key: state[key] for key in ("video_id", "discussion_post_id", "discussion_count", "like_count", "liked", "saved")}
    row = db.get(Video, video_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Video not found")
    host = request.client.host if request.client else "unknown"
    allowed, _, reset_at = check_rate_limit(ip=f"user:{user.id}:ip:{host}", endpoint="watch:interaction", max_requests=60, window_seconds=60, db=db)
    if not allowed:
        retry_after = max(1, int(reset_at - datetime.now(timezone.utc).timestamp()))
        raise HTTPException(status_code=429, detail="Rate limit exceeded", headers={"Retry-After": str(retry_after)})
    existing = db.query(model).filter_by(video_id=video_id, user_id=user.id).first()
    if existing and not active:
        db.delete(existing)
    elif not existing and active:
        db.add(model(video_id=video_id, user_id=user.id))
    db.commit()
    return {"video_id": video_id, **_interaction_state(db, row, user)}


@router.put("/{video_id}/like", response_model=VideoInteractionState)
def set_video_like(video_id: str, body: VideoInteractionUpdate, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _set_interaction(video_id, body.active, VideoLike, request, user, db)


@router.put("/{video_id}/save", response_model=VideoInteractionState)
def set_video_save(video_id: str, body: VideoInteractionUpdate, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _set_interaction(video_id, body.active, VideoSave, request, user, db)


@router.get("/{video_id}/share", response_model=VideoSharePreview)
def get_video_share_preview(video_id: str, db: Session = Depends(get_db)):
    row = _query(db).filter(Video.video_id == video_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return _share_preview(row)


@router.get("/{video_id}/preview", response_class=HTMLResponse, include_in_schema=False)
def get_video_share_page(video_id: str, db: Session = Depends(get_db)):
    row = _query(db).filter(Video.video_id == video_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Video not found")
    preview = _share_preview(row)
    values = {key: escape(str(value), quote=True) for key, value in preview.items() if key != "source"}
    source_url = escape(preview["source"]["url"], quote=True)
    source_publisher = escape(preview["source"]["publisher"], quote=True)
    return HTMLResponse(f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{values["title"]}</title>
<link rel="canonical" href="{values["canonical_url"]}"><meta property="og:type" content="video.other">
<meta property="og:title" content="{values["title"]}"><meta property="og:description" content="{values["description"]}">
<meta property="og:url" content="{values["canonical_url"]}"><meta property="og:image" content="{values["image_url"]}">
<meta name="twitter:card" content="summary_large_image"></head><body>
<main><p>Watch · Housing &amp; Rent</p><h1>{escape(row.caption)}</h1><p>{values["description"]}</p>
<p>Official source: <a href="{source_url}">{source_publisher}</a></p></main></body></html>''', headers={"Cache-Control": "public, max-age=300"})
