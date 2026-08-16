"""Privacy-safe Civic Conversation Loop ACT API.

The API prepares actions and stores optional private receipts. It never sends a
message, places a call, signs a petition, enrolls a plaintiff, or exposes member
and attendee identities publicly.
"""

from datetime import datetime, timezone
from typing import Literal, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from models.act_models import (
    ActReceipt,
    ActionCircle,
    ActionCircleMembership,
    CivicActivity,
    CivicActivityRsvp,
    OfficialOfficeContact,
)
from models.auth_models import User
from models.civic_models import Proposal
from models.database import Bill, TrackedMember, Vote, get_db
from models.issue_models import Issue, Video
from models.social_models import DiscussionPost
from services.jwt_auth import get_current_user, get_optional_user
from services.rate_limit_store import check_rate_limit


router = APIRouter(prefix="/act", tags=["act"])

ActionKind = Literal["call", "message", "follow", "event", "petition", "circle", "public_comment"]
TargetType = Literal["video", "discussion", "issue", "bill", "vote", "representative", "solution", "activity", "circle"]
ReceiptStatus = Literal["prepared", "opened", "user_confirmed_submitted", "response_received", "attended", "completed", "cancelled"]

OFFICIAL_CONTACT_HOSTS = ("house.gov", "senate.gov", "congress.gov")


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _rate_limit(request: Request, user: User, endpoint: str, maximum: int, db: Session) -> None:
    host = request.client.host if request.client else "unknown"
    allowed, _, reset_at = check_rate_limit(
        ip=f"user:{user.id}:ip:{host}", endpoint=endpoint,
        max_requests=maximum, window_seconds=60, db=db,
    )
    if not allowed:
        retry_after = max(1, int(reset_at - datetime.now(timezone.utc).timestamp()))
        raise HTTPException(status_code=429, detail="Rate limit exceeded", headers={"Retry-After": str(retry_after)})


def _safe_official_url(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    parsed = urlparse(value.strip())
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not any(host == allowed or host.endswith(f".{allowed}") for allowed in OFFICIAL_CONTACT_HOSTS):
        raise ValueError("Contact links must use an official House, Senate, or Congress HTTPS domain")
    return parsed.geturl()


def _safe_public_url(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Public activity links must be credential-free HTTPS URLs")
    return parsed.geturl()


def _target_exists(db: Session, target_type: str, target_id: str) -> bool:
    if target_type == "video": return db.get(Video, target_id) is not None
    if target_type == "issue": return db.get(Issue, target_id) is not None
    if target_type == "bill": return db.get(Bill, target_id) is not None
    if target_type == "representative": return db.query(TrackedMember).filter_by(person_id=target_id, is_active=1).first() is not None
    try:
        numeric_id = int(target_id)
    except ValueError:
        return False
    model = {
        "discussion": DiscussionPost, "vote": Vote, "solution": Proposal,
        "activity": CivicActivity, "circle": ActionCircle,
    }.get(target_type)
    return model is not None and db.get(model, numeric_id) is not None


class ReceiptWrite(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=100, pattern=r"^[A-Za-z0-9._:-]+$")
    action_kind: ActionKind
    target_type: TargetType
    target_id: str = Field(min_length=1, max_length=255)
    representative_id: Optional[str] = Field(default=None, max_length=100)
    status: ReceiptStatus
    private_note: Optional[str] = Field(default=None, max_length=2000)
    allow_aggregate: bool = False

    @field_validator("target_id", "private_note")
    @classmethod
    def trim_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class CircleCreate(BaseModel):
    name: str = Field(min_length=3, max_length=160)
    objective: str = Field(min_length=10, max_length=500)
    description: str = Field(min_length=20, max_length=10000)
    target_type: TargetType
    target_id: str = Field(min_length=1, max_length=255)
    geography: Optional[str] = Field(default=None, max_length=120)
    location_precision: Literal["none", "state", "district", "city"] = "none"
    membership_mode: Literal["open", "approval"] = "approval"
    conduct_rules: str = Field(min_length=20, max_length=5000)
    completion_condition: str = Field(min_length=10, max_length=500)

    @field_validator("name", "objective", "description", "target_id", "geography", "conduct_rules", "completion_condition")
    @classmethod
    def trim_fields(cls, value):
        return value.strip() if isinstance(value, str) else value


class ActivityCreate(BaseModel):
    circle_id: Optional[int] = Field(default=None, ge=1)
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=20, max_length=10000)
    host_type: Literal["official", "organization", "community"]
    format: Literal["in_person", "online", "hybrid"]
    starts_at: datetime
    ends_at: Optional[datetime] = None
    timezone: str = Field(min_length=1, max_length=80)
    public_location: Optional[str] = Field(default=None, max_length=500)
    public_url: Optional[str] = Field(default=None, max_length=500)
    accessibility: Optional[str] = Field(default=None, max_length=2000)
    capacity: Optional[int] = Field(default=None, ge=1, le=100000)

    @field_validator("public_url")
    @classmethod
    def validate_public_url(cls, value):
        return _safe_public_url(value)


def _contact(row: OfficialOfficeContact) -> dict:
    return {
        "id": row.id,
        "office_type": row.office_type,
        "label": row.label,
        "phone": row.phone,
        "contact_url": row.contact_url,
        "address": row.address,
        "source": {"publisher": row.source_publisher, "url": row.source_url},
        "verification_status": row.verification_status,
        "retrieved_at": row.retrieved_at.isoformat(),
        "verified_at": row.verified_at.isoformat(),
    }


def _circle(row: ActionCircle, db: Session, user: Optional[User]) -> dict:
    public_count = db.query(ActionCircleMembership).filter_by(circle_id=row.id, status="active").count()
    viewer = None
    if user:
        membership = db.query(ActionCircleMembership).filter_by(circle_id=row.id, user_id=user.id).first()
        viewer = membership.status if membership else None
    return {
        "id": row.id,
        "name": row.name,
        "objective": row.objective,
        "description": row.description,
        "target_type": row.target_type,
        "target_id": row.target_id,
        "geography": row.geography,
        "location_precision": row.location_precision,
        "membership_mode": row.membership_mode,
        "conduct_rules": row.conduct_rules,
        "completion_condition": row.completion_condition,
        "moderation_status": row.moderation_status,
        "member_count": public_count,
        "viewer_membership_status": viewer,
        "created_at": row.created_at.isoformat(),
    }


@router.get("/representatives/{person_id}")
def representative_actions(person_id: str, db: Session = Depends(get_db)):
    member = db.query(TrackedMember).filter_by(person_id=person_id, is_active=1).first()
    if member is None:
        raise HTTPException(status_code=404, detail="Representative not found")
    contacts = db.query(OfficialOfficeContact).filter_by(person_id=person_id, verification_status="verified").order_by(
        OfficialOfficeContact.office_type.asc(), OfficialOfficeContact.label.asc()
    ).all()
    return {
        "representative": {
            "person_id": member.person_id,
            "display_name": member.display_name,
            "chamber": member.chamber,
            "state": member.state,
            "party": member.party,
        },
        "contacts": [_contact(row) for row in contacts],
        "fallback": {
            "label": "U.S. Capitol Switchboard",
            "phone": "202-224-3121",
            "source": {"publisher": "U.S. Senate", "url": "https://www.senate.gov/senators/senators-contact.htm"},
        },
        "message_policy": {
            "auto_send": False,
            "delivery_claimed": False,
            "instructions": "Review your message, then copy it or open the official office form. WeThePeople does not submit it for you.",
        },
    }


@router.get("/receipts")
def list_receipts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(ActReceipt).filter_by(user_id=user.id).order_by(ActReceipt.created_at.desc(), ActReceipt.id.desc()).limit(100).all()
    return {"items": [{
        "id": row.id, "action_kind": row.action_kind, "target_type": row.target_type,
        "target_id": row.target_id, "representative_id": row.representative_id,
        "status": row.status, "private_note": row.private_note,
        "allow_aggregate": bool(row.allow_aggregate), "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    } for row in rows]}


@router.put("/receipts/{idempotency_key}")
def save_receipt(idempotency_key: str, body: ReceiptWrite, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _rate_limit(request, user, "act:receipt", 20, db)
    if idempotency_key != body.idempotency_key:
        raise HTTPException(status_code=422, detail="Idempotency key mismatch")
    row = db.query(ActReceipt).filter_by(user_id=user.id, idempotency_key=idempotency_key).first()
    immutable = (row.action_kind, row.target_type, row.target_id, row.representative_id) if row is not None else None
    incoming = (body.action_kind, body.target_type, body.target_id, body.representative_id)
    if immutable and immutable != incoming:
        raise HTTPException(status_code=409, detail="An action receipt cannot be retargeted")
    if body.representative_id and db.query(TrackedMember).filter_by(person_id=body.representative_id, is_active=1).first() is None:
        raise HTTPException(status_code=404, detail="Representative not found")
    if body.target_type == "representative" and body.representative_id not in (None, body.target_id):
        raise HTTPException(status_code=422, detail="Representative receipt target mismatch")
    if not _target_exists(db, body.target_type, body.target_id):
        raise HTTPException(status_code=404, detail="ACT target not found")
    if row is None:
        row = ActReceipt(user_id=user.id, idempotency_key=idempotency_key)
        db.add(row)
    row.action_kind, row.target_type, row.target_id, row.representative_id = incoming
    row.status = body.status
    row.private_note = body.private_note or None
    row.allow_aggregate = int(body.allow_aggregate)
    db.commit(); db.refresh(row)
    return {"id": row.id, "status": row.status, "allow_aggregate": bool(row.allow_aggregate)}


@router.get("/circles")
def list_circles(
    target_type: Optional[TargetType] = None,
    target_id: Optional[str] = Query(default=None, min_length=1, max_length=255),
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    query = db.query(ActionCircle).filter(ActionCircle.moderation_status.in_(("published", "completed")))
    if target_type: query = query.filter(ActionCircle.target_type == target_type)
    if target_id: query = query.filter(ActionCircle.target_id == target_id)
    rows = query.order_by(ActionCircle.created_at.desc(), ActionCircle.id.desc()).limit(50).all()
    return {"items": [_circle(row, db, user) for row in rows]}


@router.post("/circles", status_code=status.HTTP_201_CREATED)
def create_circle(body: CircleCreate, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _rate_limit(request, user, "act:circle-create", 3, db)
    if not _target_exists(db, body.target_type, body.target_id):
        raise HTTPException(status_code=404, detail="ACT target not found")
    row = ActionCircle(organizer_id=user.id, moderation_status="pending", **body.model_dump())
    db.add(row); db.flush()
    db.add(ActionCircleMembership(circle_id=row.id, user_id=user.id, role="organizer", status="active"))
    db.commit(); db.refresh(row)
    return {"id": row.id, "moderation_status": row.moderation_status, "message": "Circle submitted for moderation"}


@router.put("/circles/{circle_id}/membership")
def join_circle(circle_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _rate_limit(request, user, "act:circle-membership", 10, db)
    circle = db.get(ActionCircle, circle_id)
    if circle is None or circle.moderation_status != "published":
        raise HTTPException(status_code=404, detail="Action Circle not found")
    row = db.query(ActionCircleMembership).filter_by(circle_id=circle_id, user_id=user.id).first()
    next_status = "active" if circle.membership_mode == "open" else "pending"
    if row is None:
        row = ActionCircleMembership(circle_id=circle_id, user_id=user.id, role="member")
        db.add(row)
    row.status = next_status
    db.commit()
    return {"status": next_status, "member_count_is_public": True, "member_identity_is_public": False}


@router.get("/activities")
def list_activities(circle_id: Optional[int] = Query(default=None, ge=1), db: Session = Depends(get_db)):
    query = db.query(CivicActivity).filter_by(moderation_status="published")
    if circle_id: query = query.filter_by(circle_id=circle_id)
    rows = query.order_by(CivicActivity.starts_at.asc()).limit(100).all()
    return {"items": [{
        "id": row.id, "circle_id": row.circle_id, "title": row.title, "description": row.description,
        "host_type": row.host_type, "format": row.format, "starts_at": row.starts_at.isoformat(),
        "ends_at": row.ends_at.isoformat() if row.ends_at else None, "timezone": row.timezone,
        "public_location": row.public_location, "public_url": row.public_url,
        "accessibility": row.accessibility, "capacity": row.capacity,
    } for row in rows]}


@router.post("/activities", status_code=status.HTTP_201_CREATED)
def create_activity(body: ActivityCreate, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _rate_limit(request, user, "act:activity-create", 5, db)
    if body.ends_at and _utc(body.ends_at) <= _utc(body.starts_at):
        raise HTTPException(status_code=422, detail="Activity end must be after its start")
    if _utc(body.starts_at) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="Activity must start in the future")
    if body.circle_id:
        membership = db.query(ActionCircleMembership).filter_by(circle_id=body.circle_id, user_id=user.id, status="active").first()
        if membership is None or membership.role not in ("organizer", "moderator"):
            raise HTTPException(status_code=403, detail="Only Circle organizers or moderators may add activities")
    row = CivicActivity(organizer_id=user.id, moderation_status="pending", **body.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return {"id": row.id, "moderation_status": row.moderation_status, "message": "Activity submitted for moderation"}


@router.put("/activities/{activity_id}/rsvp")
def rsvp_activity(activity_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _rate_limit(request, user, "act:activity-rsvp", 10, db)
    activity = db.get(CivicActivity, activity_id)
    if activity is None or activity.moderation_status != "published":
        raise HTTPException(status_code=404, detail="Activity not found")
    if _utc(activity.starts_at) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=409, detail="This activity has already started")
    row = db.query(CivicActivityRsvp).filter_by(activity_id=activity_id, user_id=user.id).first()
    if row is None or row.status != "going":
        if activity.capacity:
            going = db.query(CivicActivityRsvp).filter_by(activity_id=activity_id, status="going").count()
            if going >= activity.capacity:
                raise HTTPException(status_code=409, detail="Activity capacity reached")
    if row is None:
        row = CivicActivityRsvp(activity_id=activity_id, user_id=user.id, status="going")
        db.add(row)
    else:
        row.status = "going"
    db.commit()
    return {"status": "going", "attendee_identity_is_public": False}


@router.delete("/activities/{activity_id}/rsvp", status_code=status.HTTP_204_NO_CONTENT)
def cancel_rsvp(activity_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _rate_limit(request, user, "act:activity-rsvp", 10, db)
    row = db.query(CivicActivityRsvp).filter_by(activity_id=activity_id, user_id=user.id).first()
    if row:
        row.status = "cancelled"; db.commit()
    return None


@router.get("/legal-pathways")
def legal_pathway_gate():
    return {
        "enabled": False,
        "actions": [],
        "message": "Legal pathways require separate legal, privacy, source-verification, and operator approval. WeThePeople does not determine eligibility or enroll plaintiffs.",
    }


@router.get("/petitions")
def petition_gate():
    return {
        "enabled": False,
        "actions": [],
        "message": "Petitions require verified ownership, complete terms, signer privacy controls, moderation, and an auditable delivery process. WeThePeople does not collect signatures until those gates are approved.",
    }
