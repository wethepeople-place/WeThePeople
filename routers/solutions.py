"""Bounded citizen solutions with canonical identity and transparent vote rules."""

from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from models.auth_models import User
from models.civic_models import Proposal, SolutionRevision, SolutionVote
from models.database import get_db
from models.issue_models import Issue
from models.social_models import DiscussionAttachment, DiscussionPost, DiscussionVideoLink
from routers.discussions import _social_link
from services.jwt_auth import get_current_user, get_optional_user
from services.rate_limit_store import check_rate_limit

router = APIRouter(prefix="/solutions", tags=["solutions"])
VOTE_RULE = "One equal-weight current vote per authenticated user. Results reflect participating users only; they are not a scientific or representative poll."


class SolutionCreate(BaseModel):
    issue_slug: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=5, max_length=500)
    summary: str = Field(min_length=10, max_length=1000)
    body: str = Field(min_length=20, max_length=10000)
    video_url: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("issue_slug", "title", "summary", "body")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value must contain text")
        return value


class SolutionEdit(BaseModel):
    title: str = Field(min_length=5, max_length=500)
    summary: str = Field(min_length=10, max_length=1000)
    body: str = Field(min_length=20, max_length=10000)
    change_note: str = Field(min_length=3, max_length=500)


class VoteSet(BaseModel):
    choice: Optional[Literal["support", "oppose"]] = None


def _rate_limit(request: Request, user: User, endpoint: str, maximum: int, db: Session) -> None:
    host = request.client.host if request.client else "unknown"
    allowed, _, reset_at = check_rate_limit(
        ip=f"user:{user.id}:ip:{host}", endpoint=endpoint, max_requests=maximum, window_seconds=60, db=db,
    )
    if not allowed:
        retry_after = max(1, int(reset_at - datetime.now(timezone.utc).timestamp()))
        raise HTTPException(status_code=429, detail="Rate limit exceeded", headers={"Retry-After": str(retry_after)})


def _totals(solution_id: int, db: Session) -> dict:
    rows = db.query(SolutionVote.choice, func.count(SolutionVote.id)).filter_by(solution_id=solution_id).group_by(SolutionVote.choice).all()
    counts = {"support": 0, "oppose": 0}
    counts.update({choice: count for choice, count in rows})
    return {**counts, "total_ballots": counts["support"] + counts["oppose"]}


def _serialize(row: Proposal, db: Session, user: Optional[User] = None, include_body: bool = False) -> dict:
    vote = None
    if user is not None:
        current = db.query(SolutionVote).filter_by(solution_id=row.id, voter_user_id=user.id).first()
        vote = current.choice if current else None
    creator = db.get(User, row.author_id)
    discussion = db.query(DiscussionAttachment).join(DiscussionPost).filter(
        DiscussionAttachment.solution_id == row.id,
        DiscussionAttachment.attachment_type == "solution",
        DiscussionPost.moderation_status == "published",
    ).order_by(DiscussionAttachment.post_id).first()
    payload = {
        "id": row.id, "creator_user_id": row.author_id, "issue_slug": row.issue_slug,
        "creator_display_name": (creator.display_name or "Participant") if creator else "Participant",
        "title": row.title, "summary": row.summary, "status": row.status,
        "latest_revision_number": row.latest_revision_number, "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat() if row.updated_at else row.created_at.isoformat(),
        "published_at": row.published_at.isoformat() if row.published_at else None,
        "vote_totals": _totals(row.id, db), "current_user_choice": vote,
        "vote_rule": VOTE_RULE, "vote_choices": ["support", "oppose"],
        "discussion_post_id": discussion.post_id if discussion else None,
        "video_link": ({
            "provider": discussion.post.video_link.provider,
            "provider_video_id": discussion.post.video_link.provider_video_id,
            "canonical_url": discussion.post.video_link.canonical_url,
        } if discussion and discussion.post.video_link else None),
    }
    if include_body:
        payload.update({"body": row.body, "duplicate_of_solution_id": row.duplicate_of_id})
    return payload


def _visible_solution(solution_id: int, db: Session) -> Proposal:
    row = db.get(Proposal, solution_id)
    if row is None or row.status not in {"published", "closed", "duplicate", "removed"} or row.issue_slug is None:
        raise HTTPException(status_code=404, detail="Solution not found")
    return row


def _mutable_solution(solution_id: int, db: Session) -> Proposal:
    row = _visible_solution(solution_id, db)
    if row.status != "published":
        raise HTTPException(status_code=409, detail="This solution no longer accepts changes or votes")
    return row


@router.get("")
def list_solutions(
    issue_slug: str = Query(..., max_length=100), limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0), user: Optional[User] = Depends(get_optional_user), db: Session = Depends(get_db),
):
    query = db.query(Proposal).filter_by(issue_slug=issue_slug, status="published")
    total = query.count()
    rows = query.order_by(Proposal.published_at.desc(), Proposal.id.desc()).offset(offset).limit(limit).all()
    return {"total": total, "limit": limit, "offset": offset, "items": [_serialize(row, db, user) for row in rows]}


@router.get("/{solution_id}")
def get_solution(solution_id: int, issue_slug: Optional[str] = Query(None, max_length=100), user: Optional[User] = Depends(get_optional_user), db: Session = Depends(get_db)):
    row = _visible_solution(solution_id, db)
    if issue_slug is not None and row.issue_slug != issue_slug:
        raise HTTPException(status_code=404, detail="Solution not found for this issue")
    if row.status == "removed":
        return {"id": row.id, "issue_slug": row.issue_slug, "status": "removed", "message": "This solution was removed."}
    if row.status == "duplicate":
        return {"id": row.id, "issue_slug": row.issue_slug, "status": "duplicate", "message": "This solution was marked as a duplicate.", "duplicate_of_solution_id": row.duplicate_of_id}
    return _serialize(row, db, user, include_body=True)


@router.get("/{solution_id}/revisions")
def list_revisions(solution_id: int, db: Session = Depends(get_db)):
    row = _visible_solution(solution_id, db)
    if row.status in {"duplicate", "removed"}:
        raise HTTPException(status_code=404, detail="Revision history is unavailable")
    revisions = db.query(SolutionRevision).filter_by(solution_id=solution_id).order_by(SolutionRevision.revision_number.desc()).all()
    return {"solution_id": solution_id, "latest_revision_number": row.latest_revision_number, "items": [{
        "revision_number": item.revision_number, "title": item.title, "summary": item.summary, "body": item.body,
        "change_note": item.change_note, "created_at": item.created_at.isoformat(),
        "editor_display_name": ((db.get(User, item.editor_user_id).display_name or "Participant") if db.get(User, item.editor_user_id) else "Participant"),
    } for item in revisions]}


@router.post("", status_code=201)
def create_solution(body: SolutionCreate, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _rate_limit(request, user, "solution_create", 5, db)
    if db.get(Issue, body.issue_slug) is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    row = Proposal(author_id=user.id, issue_slug=body.issue_slug, title=body.title, summary=body.summary, body=body.body,
                   status="published", published_at=datetime.now(timezone.utc), latest_revision_number=1)
    db.add(row)
    db.flush()
    video_link = _social_link(body.video_url) if body.video_url else None
    if video_link:
        provider, provider_video_id, canonical_url = video_link
        discussion = DiscussionPost(
            author_id=user.id, author_label=user.display_name or "Community member",
            body=body.body, moderation_status="published",
            video_link=DiscussionVideoLink(
                provider=provider, provider_video_id=provider_video_id, canonical_url=canonical_url,
            ),
        )
        discussion.attachments.extend([
            DiscussionAttachment(attachment_type="issue", issue_slug=row.issue_slug, label=db.get(Issue, row.issue_slug).title),
            DiscussionAttachment(attachment_type="solution", solution_id=row.id, label=row.title),
        ])
        db.add(discussion)
    db.add(SolutionRevision(solution_id=row.id, editor_user_id=user.id, revision_number=1, title=row.title,
                            summary=row.summary, body=row.body, change_note="Initial publication"))
    db.commit()
    return _serialize(row, db, user, include_body=True)


@router.put("/{solution_id}")
def edit_solution(solution_id: int, body: SolutionEdit, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _rate_limit(request, user, "solution_edit", 10, db)
    row = _mutable_solution(solution_id, db)
    if row.author_id != user.id:
        raise HTTPException(status_code=403, detail="Only the creator can revise this solution")
    row.latest_revision_number += 1
    row.title, row.summary, row.body = body.title.strip(), body.summary.strip(), body.body.strip()
    db.add(SolutionRevision(solution_id=row.id, editor_user_id=user.id, revision_number=row.latest_revision_number,
                            title=row.title, summary=row.summary, body=row.body, change_note=body.change_note.strip()))
    db.commit()
    return _serialize(row, db, user, include_body=True)


@router.put("/{solution_id}/vote")
def set_vote(solution_id: int, body: VoteSet, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _rate_limit(request, user, "solution_vote", 20, db)
    _mutable_solution(solution_id, db)
    row = db.query(SolutionVote).filter_by(solution_id=solution_id, voter_user_id=user.id).first()
    if body.choice is None:
        if row is not None:
            db.delete(row)
    elif row is None:
        db.add(SolutionVote(solution_id=solution_id, voter_user_id=user.id, choice=body.choice))
    else:
        row.choice = body.choice
    db.commit()
    return {"current_user_choice": body.choice, "vote_totals": _totals(solution_id, db), "vote_rule": VOTE_RULE}
