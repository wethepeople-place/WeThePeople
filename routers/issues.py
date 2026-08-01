"""Read-only, source-first issue endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload, selectinload

from models.database import Bill, SourceDocument, get_db
from models.issue_models import EvidenceObservation, EvidenceSeries, Issue, IssueBill
from models.response_schemas import (
    IssueBillsResponse,
    IssueEvidenceResponse,
    IssueSummaryResponse,
)


router = APIRouter(prefix="/issues", tags=["issues"])


def _get_issue_or_404(slug: str, db: Session) -> Issue:
    issue = db.get(Issue, slug)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    return issue


def _source(source: SourceDocument | None) -> dict:
    """Return normalized provenance, failing closed when it is incomplete."""
    if (
        source is None
        or not source.url
        or not source.url.lower().startswith("https://")
        or not source.publisher
        or source.retrieved_at is None
    ):
        raise HTTPException(status_code=503, detail="Authoritative source metadata is incomplete")
    return {
        "url": source.url,
        "publisher": source.publisher,
        "retrieved_at": source.retrieved_at.isoformat(),
    }


@router.get("/{slug}", response_model=IssueSummaryResponse)
def get_issue(slug: str, db: Session = Depends(get_db)):
    issue = _get_issue_or_404(slug, db)
    return {
        "slug": issue.slug,
        "title": issue.title,
        "summary": issue.summary,
        "evidence_series_count": (
            db.query(EvidenceSeries).filter(EvidenceSeries.issue_slug == slug).count()
        ),
        "bill_count": db.query(IssueBill).filter(IssueBill.issue_slug == slug).count(),
    }


@router.get("/{slug}/evidence", response_model=IssueEvidenceResponse)
def get_issue_evidence(slug: str, db: Session = Depends(get_db)):
    _get_issue_or_404(slug, db)
    rows = (
        db.query(EvidenceSeries)
        .options(
            joinedload(EvidenceSeries.source),
            selectinload(EvidenceSeries.observations).joinedload(EvidenceObservation.source),
        )
        .filter(EvidenceSeries.issue_slug == slug)
        .order_by(EvidenceSeries.key)
        .all()
    )
    series = []
    for row in rows:
        observations = sorted(row.observations, key=lambda item: item.observation_date)
        series.append(
            {
                "key": row.key,
                "title": row.title,
                "unit": row.unit,
                "geography": {"type": row.geography_type, "id": row.geography_id},
                "source": _source(row.source),
                "observations": [
                    {
                        "date": item.observation_date.isoformat(),
                        "value": item.value,
                        "source_record_id": item.source_record_id,
                        "source": _source(item.source),
                    }
                    for item in observations
                ],
            }
        )
    return {"issue_slug": slug, "total": len(series), "series": series}


@router.get("/{slug}/bills", response_model=IssueBillsResponse)
def get_issue_bills(slug: str, db: Session = Depends(get_db)):
    _get_issue_or_404(slug, db)
    rows = (
        db.query(IssueBill)
        .options(joinedload(IssueBill.source), joinedload(IssueBill.bill))
        .join(Bill, Bill.bill_id == IssueBill.bill_id)
        .filter(IssueBill.issue_slug == slug)
        .order_by(Bill.congress.desc(), Bill.bill_type, Bill.bill_number)
        .all()
    )
    bills = [
        {
            "bill_id": row.bill.bill_id,
            "congress": row.bill.congress,
            "bill_type": row.bill.bill_type,
            "bill_number": row.bill.bill_number,
            "title": row.bill.title,
            "policy_area": row.bill.policy_area,
            "phase": row.phase,
            "status_bucket": row.bill.status_bucket,
            "status_reason": row.bill.status_reason,
            "latest_action_text": row.bill.latest_action_text,
            "latest_action_date": (
                row.bill.latest_action_date.isoformat() if row.bill.latest_action_date else None
            ),
            "relevance_note": row.relevance_note,
            "source": _source(row.source),
        }
        for row in rows
    ]
    return {"issue_slug": slug, "total": len(bills), "bills": bills}
