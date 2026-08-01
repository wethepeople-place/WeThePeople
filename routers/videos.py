"""Public, read-only Watch video endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload, selectinload

from models.database import get_db
from models.issue_models import Video, VideoBill, VideoIssue
from models.response_schemas import VideoItem, VideosResponse
from routers.issues import _source

router = APIRouter(prefix="/videos", tags=["videos"])


def _query(db: Session):
    return db.query(Video).options(
        joinedload(Video.source),
        selectinload(Video.issue_links).joinedload(VideoIssue.issue),
        selectinload(Video.bill_links).joinedload(VideoBill.bill),
    )


def _serialize(row: Video) -> dict:
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
        "published_at": row.published_at.isoformat(),
        "source": _source(row.source),
        "issue": {"slug": issue.slug, "title": issue.title},
        "bills": [{"bill_id": bill.bill_id, "title": bill.title} for bill in bills],
    }


@router.get("", response_model=VideosResponse)
def list_videos(db: Session = Depends(get_db)):
    rows = _query(db).order_by(Video.sort_order.asc(), Video.published_at.desc(), Video.video_id).all()
    return {"total": len(rows), "videos": [_serialize(row) for row in rows]}


@router.get("/{video_id}", response_model=VideoItem)
def get_video(video_id: str, db: Session = Depends(get_db)):
    row = _query(db).filter(Video.video_id == video_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return _serialize(row)
