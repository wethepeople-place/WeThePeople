"""Public, read-only Watch video endpoints."""

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime
from html import escape
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session, joinedload, selectinload

from models.database import get_db
from models.issue_models import Video, VideoBill, VideoIssue
from models.response_schemas import VideoItem, VideoSharePreview, VideosResponse
from models.social_models import DiscussionAttachment, DiscussionPost
from routers.issues import _source

router = APIRouter(prefix="/videos", tags=["videos"])
PUBLIC_WEB_ORIGIN = os.getenv("WTP_PUBLIC_WEB_ORIGIN", "https://wethepeople.place").rstrip("/")
CURSOR_SECRET = os.getenv("WTP_VIDEO_CURSOR_SECRET", "development-only-watch-cursor").encode()
WATCH_FIXTURE_PATH = Path(__file__).resolve().parents[1] / "data" / "watch_housing_rent.json"


def _fixture_delivery(video_id: str) -> dict | None:
    """Return optional delivery metadata without adding it to the database schema."""
    if os.getenv("WTP_ENV") != "development" or os.getenv("WTP_ENABLE_DEVELOPMENT_WATCH_EMBED") != "true":
        return None
    try:
        payload = json.loads(WATCH_FIXTURE_PATH.read_text(encoding="utf-8"))
        record = next(item for item in payload.get("videos", ()) if item.get("video_id") == video_id)
        delivery = record.get("delivery")
        if not isinstance(delivery, dict):
            return None
        canonical_url = delivery.get("canonical_url")
        mode = delivery.get("mode")
        if mode not in {"official_embed", "hosted_video", "link_out"} or not isinstance(canonical_url, str) or not canonical_url.startswith("https://"):
            return None
        if mode == "official_embed" and not all(delivery.get(field) for field in ("provider", "provider_video_id", "source_label")):
            return {"mode": "link_out", "canonical_url": canonical_url, "development_only": bool(delivery.get("development_only"))}
        return delivery
    except (OSError, ValueError, StopIteration, TypeError):
        return None


def _fixture_accessibility(video_id: str) -> dict | None:
    """Return development-authorized accessibility metadata from the fixture."""
    if os.getenv("WTP_ENV") != "development" or os.getenv("WTP_ENABLE_DEVELOPMENT_WATCH_EMBED") != "true":
        return None
    try:
        payload = json.loads(WATCH_FIXTURE_PATH.read_text(encoding="utf-8"))
        record = next(item for item in payload.get("videos", ()) if item.get("video_id") == video_id)
        accessibility = record.get("accessibility")
        if not isinstance(accessibility, dict):
            return None
        transcript_url = accessibility.get("official_transcript_url")
        if accessibility.get("text_kind") not in {"overview", "transcript"} or not isinstance(transcript_url, str) or not transcript_url.startswith("https://") or not accessibility.get("official_transcript_label"):
            return None
        return accessibility
    except (OSError, ValueError, StopIteration, TypeError):
        return None


def _cursor(row: Video) -> str:
    payload = json.dumps({"v": 1, "s": row.sort_order, "p": row.published_at.isoformat(), "i": row.video_id}, separators=(",", ":"), sort_keys=True).encode()
    signature = hmac.new(CURSOR_SECRET, payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(payload + signature).decode().rstrip("=")


def _decode_cursor(value: str) -> tuple[int, datetime, str]:
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        payload, signature = raw[:-32], raw[-32:]
        if not hmac.compare_digest(signature, hmac.new(CURSOR_SECRET, payload, hashlib.sha256).digest()):
            raise ValueError
        data = json.loads(payload)
        if data.get("v") != 1:
            raise ValueError
        return int(data["s"]), datetime.fromisoformat(data["p"]), str(data["i"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise HTTPException(status_code=400, detail="Invalid video cursor") from None


def _share_preview(row: Video) -> dict:
    item = _serialize(row)
    return {
        "video_id": row.video_id,
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


def _discussion_post_id(db: Session, row: Video) -> int | None:
    issue_slug = row.issue_links[0].issue_slug if row.issue_links else None
    direct = db.query(DiscussionAttachment.post_id).join(DiscussionPost).filter(
        DiscussionAttachment.attachment_type == "video",
        DiscussionAttachment.video_id == row.video_id,
        DiscussionPost.moderation_status == "published",
    ).order_by(DiscussionAttachment.post_id).first()
    if direct:
        return direct[0]
    fallback = db.query(DiscussionAttachment.post_id).join(DiscussionPost).filter(
        DiscussionAttachment.attachment_type == "issue",
        DiscussionAttachment.issue_slug == issue_slug,
        DiscussionPost.moderation_status == "published",
    ).order_by(DiscussionAttachment.post_id).first()
    return fallback[0] if fallback else None


def _serialize(row: Video, discussion_post_id: int | None = None) -> dict:
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
        "discussion_post_id": discussion_post_id,
    }


@router.get("", response_model=VideosResponse)
def list_videos(cursor: str | None = None, limit: int = Query(10, ge=1, le=25), db: Session = Depends(get_db)):
    query = _query(db)
    total = query.count()
    if cursor:
        sort_order, published_at, video_id = _decode_cursor(cursor)
        query = query.filter(or_(
            Video.sort_order > sort_order,
            and_(Video.sort_order == sort_order, Video.published_at < published_at),
            and_(Video.sort_order == sort_order, Video.published_at == published_at, Video.video_id > video_id),
        ))
    rows = query.order_by(Video.sort_order.asc(), Video.published_at.desc(), Video.video_id.asc()).limit(limit + 1).all()
    has_more = len(rows) > limit
    page = rows[:limit]
    return {"total": total, "videos": [_serialize(row, _discussion_post_id(db, row)) for row in page], "next_cursor": _cursor(page[-1]) if has_more and page else None, "has_more": has_more}


@router.get("/{video_id}", response_model=VideoItem)
def get_video(video_id: str, db: Session = Depends(get_db)):
    row = _query(db).filter(Video.video_id == video_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return _serialize(row, _discussion_post_id(db, row))


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
