from datetime import date, datetime, timezone

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from models.committee_models import Committee
from models.database import Base, Bill, BillAction, SourceDocument
from models.issue_models import (
    BillCommitteeReferral,
    EvidenceObservation,
    EvidenceSeries,
    Issue,
    IssueBill,
)


def test_issue_schema_reuses_canonical_civic_tables_and_provenance(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'housing-rent-schema.db'}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    expected_tables = {
        "issues",
        "evidence_series",
        "evidence_observations",
        "issue_bills",
        "bill_committee_referrals",
    }
    assert expected_tables <= set(inspect(engine).get_table_names())

    retrieved_at = datetime(2026, 7, 31, tzinfo=timezone.utc)
    with Session() as session:
        hud = SourceDocument(
            url="https://www.huduser.gov/portal/dataset/fmr-api.html",
            publisher="U.S. Department of Housing and Urban Development",
            retrieved_at=retrieved_at,
        )
        congress = SourceDocument(
            url="https://www.congress.gov/bill/119th-congress/senate-bill/968",
            publisher="Congress.gov",
            retrieved_at=retrieved_at,
        )
        session.add_all([hud, congress])
        session.flush()

        issue = Issue(slug="housing-rent", title="Housing & Rent")
        series = EvidenceSeries(
            issue=issue,
            key="median_rent",
            title="HUD Fair Market Rent",
            unit="USD per month",
            geography_type="national",
            geography_id="US",
            source=hud,
        )
        series.observations.append(
            EvidenceObservation(
                observation_date=date(2026, 1, 1),
                value=1500.0,
                source=hud,
                source_record_id="HUD-FMR-2026-US",
            )
        )
        bill = Bill(
            bill_id="s968-119",
            congress=119,
            bill_type="s",
            bill_number=968,
            title="Rent Relief Act of 2025",
            status_bucket="introduced",
        )
        issue.bill_links.append(
            IssueBill(
                bill=bill,
                phase="upcoming",
                source=congress,
                relevance_note="Refundable renter tax credit.",
            )
        )
        committee = Committee(
            thomas_id="SSFI",
            name="Senate Committee on Finance",
            chamber="senate",
            url="https://www.finance.senate.gov/",
        )
        action = BillAction(
            bill=bill,
            action_date=retrieved_at,
            action_text="Read twice and referred to the Committee on Finance.",
            committee="Senate Committee on Finance",
        )
        session.add_all([series, bill, committee, action])
        session.flush()
        session.add(
            BillCommitteeReferral(
                bill=bill,
                committee=committee,
                bill_action=action,
                referred_at=date(2025, 3, 11),
                source=congress,
            )
        )
        session.commit()

        stored_issue = session.get(Issue, "housing-rent")
        stored_retrieved_at = stored_issue.evidence_series[0].source.retrieved_at
        assert stored_retrieved_at.replace(tzinfo=timezone.utc) == retrieved_at
        assert stored_issue.evidence_series[0].observations[0].source_record_id == "HUD-FMR-2026-US"
        assert stored_issue.bill_links[0].bill is bill
        assert bill.committee_referrals[0].committee.thomas_id == "SSFI"
        assert bill.committee_referrals[0].source.publisher == "Congress.gov"


def test_public_slice_relationships_require_normalized_sources():
    for model in (EvidenceSeries, EvidenceObservation, IssueBill, BillCommitteeReferral):
        assert model.__table__.c.source_id.nullable is False
