"""Read-only, source-first issue endpoints."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload, selectinload

from jobs.load_agenda_priorities import AGENDA_FIXTURE_PATH, validate_fixture
from models.database import Bill, SourceDocument, get_db
from models.issue_models import EvidenceObservation, EvidenceSeries, Issue, IssueBill
from models.response_schemas import (
    IssueAgendaResponse,
    IssueBillsResponse,
    IssueEvidenceResponse,
    IssueSummaryResponse,
)


router = APIRouter(prefix="/issues", tags=["issues"])


@router.get("", response_model=IssueAgendaResponse)
def list_issue_agenda(db: Session = Depends(get_db)):
    """Return the reviewed public-priorities Agenda without implying WTP popularity."""
    payload = json.loads(AGENDA_FIXTURE_PATH.read_text(encoding="utf-8"))
    validate_fixture(payload)
    methodology = payload["methodology"]
    priority_items = payload["items"]
    priorities = {item["slug"]: item for item in priority_items}
    issues = db.query(Issue).filter(Issue.slug.in_(priorities)).all()
    issue_by_slug = {issue.slug: issue for issue in issues}
    items = []
    for priority in priority_items:
        issue = issue_by_slug.get(priority["slug"])
        if issue is None:
            continue
        series = (
            db.query(EvidenceSeries)
            .options(selectinload(EvidenceSeries.observations))
            .filter(EvidenceSeries.issue_slug == issue.slug)
            .all()
        )
        observations = [observation for row in series for observation in row.observations]
        latest = max(observations, key=lambda item: item.observation_date, default=None)
        latest_series = next(
            (row for row in series if latest is not None and row.id == latest.series_id),
            None,
        )
        evidence_note = None
        if latest is not None and latest_series is not None:
            value = f"{latest.value:g}"
            evidence_note = (
                f"{latest_series.title}: {value} {latest_series.unit} "
                f"({latest.observation_date.isoformat()})"
            )
        items.append({
            "rank": priority["rank"],
            "slug": issue.slug,
            "title": issue.title,
            "summary": issue.summary,
            "evidence_note": evidence_note,
            "evidence_series_count": len(series),
            "bill_count": db.query(IssueBill).filter(IssueBill.issue_slug == issue.slug).count(),
            "latest_evidence_date": latest.observation_date.isoformat() if latest else None,
            "priority_share": priority["priority_share"],
            "priority_note": f"{priority['priority_share']}% named this as a 2026 government priority",
            "community_score": None,
        })

    return {
        "total": len(items),
        "methodology": {
            "kind": "public_priorities_poll",
            "label": methodology["label"],
            "description": methodology["description"],
            "community_ranked": False,
            "sample_size": methodology["sample_size"],
            "survey_start": methodology["survey_start"],
            "survey_end": methodology["survey_end"],
            "margin_of_error_points": methodology["margin_of_error_points"],
            "source_url": methodology["source_url"],
            "publisher": methodology["publisher"],
            "question": methodology["question"],
            "tie_break": methodology["tie_break"],
            "updated_at": methodology["survey_end"],
        },
        "items": items,
    }


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
