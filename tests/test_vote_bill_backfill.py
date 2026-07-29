from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from connectors.congress_votes import backfill_related_bills
from models.database import Base, Bill, BillAction, Vote
from routers import politics_bills


def test_vote_reference_creates_sourced_bill_shell_and_is_idempotent(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'vote-bill.db'}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        session.add(Vote(
            congress=119,
            chamber="house",
            roll_number=74,
            vote_session=2,
            question="On Agreeing to the Resolution",
            vote_date=date(2026, 2, 24),
            related_bill_congress=119,
            related_bill_type="HRES",
            related_bill_number=1075,
            result="Passed",
            yea_count=208,
            nay_count=187,
            source_url="https://clerk.house.gov/Votes/202674",
            metadata_json={
                "legislationUrl": (
                    "https://www.congress.gov/bill/119th-congress/"
                    "house-resolution/1075"
                ),
            },
        ))
        session.commit()

        assert backfill_related_bills(session) == 1
        assert backfill_related_bills(session) == 0

        bill = session.query(Bill).one()
        assert bill.bill_id == "hres1075-119"
        assert bill.title == "H.Res. 1075"
        assert bill.status_bucket == "passed_house"
        assert bill.metadata_json["record_status"] == "vote-sourced-shell"
        assert bill.metadata_json["vote_source_url"].endswith("/202674")
        assert bill.needs_enrichment == 1

        action = session.query(BillAction).one()
        assert action.bill_id == bill.bill_id
        assert action.action_code == "recorded-vote"
        assert action.raw_json["source_url"].endswith("/202674")

        monkeypatch.setattr(politics_bills, "SessionLocal", Session)
        response = politics_bills.get_bill("hres1075-119")
        assert response["congress_url"].endswith("/house-resolution/1075")
        assert response["timeline"][0]["action_type"] == "recorded-vote"
