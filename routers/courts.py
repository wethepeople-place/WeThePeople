"""Read-only, source-first court case endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload, selectinload

from models.court_models import BillCourtCase, CourtCase, CourtEvent, IssueCourtCase
from models.database import get_db
from routers.issues import _source

router = APIRouter(prefix="/courts", tags=["courts"])


def _case_item(row: CourtCase) -> dict:
    if not row.docket_url.lower().startswith("https://"):
        raise HTTPException(status_code=503, detail="Authoritative court docket URL is incomplete")
    return {
        "case_id": row.case_id, "case_name": row.case_name, "court_name": row.court_name,
        "jurisdiction": row.jurisdiction, "docket_number": row.docket_number,
        "filed_date": row.filed_date.isoformat(), "procedural_status": row.procedural_status,
        "disposition": row.disposition, "docket_url": row.docket_url,
        "last_verified_at": row.last_verified_at.isoformat(), "source": _source(row.source),
    }


@router.get("")
def list_court_cases(
    issue_slug: str | None = Query(default=None, min_length=1, max_length=100),
    bill_id: str | None = Query(default=None, min_length=1, max_length=150),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(CourtCase).options(joinedload(CourtCase.source))
    if issue_slug:
        query = query.join(IssueCourtCase).filter(IssueCourtCase.issue_slug == issue_slug)
    if bill_id:
        query = query.join(BillCourtCase).filter(BillCourtCase.bill_id == bill_id)
    total = query.count()
    rows = query.order_by(CourtCase.filed_date.desc(), CourtCase.case_id).offset(offset).limit(limit).all()
    return {"total": total, "limit": limit, "offset": offset, "items": [_case_item(row) for row in rows]}


@router.get("/{case_id}")
def get_court_case(case_id: str, db: Session = Depends(get_db)):
    row = db.query(CourtCase).options(joinedload(CourtCase.source), selectinload(CourtCase.parties), selectinload(CourtCase.events).joinedload(CourtEvent.source)).filter(CourtCase.case_id == case_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Court case not found")
    payload = _case_item(row)
    payload["parties"] = [{"name": item.name, "role": item.role, "entity_type": item.entity_type, "entity_id": item.entity_id} for item in sorted(row.parties, key=lambda item: (item.role, item.name))]
    payload["events"] = [{
        "id": item.id, "event_date": item.event_date.isoformat(), "event_type": item.event_type,
        "assertion_kind": item.assertion_kind, "summary": item.summary,
        "document_url": item.document_url, "source": _source(item.source),
    } for item in sorted(row.events, key=lambda item: (item.event_date, item.id))]
    return payload
