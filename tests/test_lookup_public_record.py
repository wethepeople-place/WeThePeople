from datetime import date
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models.database import Base, Bill, MemberVote, TrackedMember, Vote
from routers import lookup


def test_latest_vote_includes_related_bill_title(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        member = TrackedMember(
            person_id="andy_harris",
            bioguide_id="H001052",
            display_name="Andy Harris",
            chamber="house",
            state="MD",
            party="R",
            is_active=1,
        )
        bill = Bill(
            bill_id="hres1075-119",
            congress=119,
            bill_type="hres",
            bill_number=1075,
            title="Stop Insider Trading Act",
        )
        vote = Vote(
            congress=119,
            chamber="house",
            roll_number=42,
            question="HRES1075",
            vote_date=date(2026, 2, 24),
            related_bill_congress=119,
            related_bill_type="HRES",
            related_bill_number=1075,
            result="Passed",
            source_url="https://www.congress.gov/vote/119th-congress/house-vote/42",
        )
        session.add_all([member, bill, vote])
        session.flush()
        session.add(MemberVote(
            vote_id=vote.id,
            person_id=member.person_id,
            bioguide_id=member.bioguide_id,
            member_name=member.display_name,
            party=member.party,
            state=member.state,
            position="Yea",
        ))
        session.commit()

        monkeypatch.setattr(lookup, "_zip_overrides", {
            "99999": {"state": "MD", "house_person_id": "andy_harris"},
        })
        response = lookup.zip_lookup("99999", session)

    latest_vote = response["representatives"][0]["votes"][0]
    assert latest_vote["bill_title"] == "Stop Insider Trading Act"
    assert latest_vote["related_bill"] == "HRES1075"


def test_connected_record_reuses_contact_office_panel():
    source = (Path(__file__).resolve().parents[1] / "frontend" / "src" / "pages" / "RepresentativeLookupPage.tsx").read_text(encoding="utf-8")
    assert 'buttonVariant="compact"' in source
    assert "issueSlug={issueSlug}" in source
