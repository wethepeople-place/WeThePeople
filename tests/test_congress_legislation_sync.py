from jobs.sync_congress_legislation import (
    CongressClient,
    classify_status,
    run,
)
from models.database import Bill, BillAction, MemberBillGroundTruth


class Response:
    status_code = 200
    text = ""

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class FakeHTTP:
    def __init__(self):
        self.calls = []

    def get(self, url, params, timeout):
        self.calls.append((url, params))
        path = url.removeprefix("https://api.congress.gov/v3")
        payloads = {
            "/bill/119": {"bills": [{"congress": 119, "type": "S", "number": "3270", "title": "A postal facility bill", "updateDate": "2026-08-06", "latestAction": {"actionDate": "2026-08-06", "text": "Committee on Homeland Security and Governmental Affairs. Ordered to be reported favorably."}}], "pagination": {"count": 1}},
            "/bill/119/s/3270": {"bill": {"congress": 119, "type": "S", "number": "3270", "title": "A postal facility bill", "introducedDate": "2025-11-20", "updateDate": "2026-08-06", "policyArea": {"name": "Government Operations and Politics"}, "sponsors": [{"bioguideId": "V000128", "fullName": "Sen. Van Hollen"}], "latestAction": {"actionDate": "2026-08-06", "text": "Committee on Homeland Security and Governmental Affairs. Ordered to be reported favorably."}}},
            "/bill/119/s/3270/actions": {"actions": [{"actionDate": "2025-11-20", "text": "Read twice and referred to the Committee on Homeland Security and Governmental Affairs.", "actionCode": "IntroReferral"}, {"actionDate": "2026-08-06", "text": "Committee on Homeland Security and Governmental Affairs. Ordered to be reported favorably."}, {"actionDate": "2026-08-06", "text": "Committee on Homeland Security and Governmental Affairs. Ordered to be reported favorably."}], "pagination": {"count": 3}},
            "/bill/119/s/3270/cosponsors": {"cosponsors": [{"bioguideId": "A000055", "fullName": "Sen. Alsobrooks"}], "pagination": {"count": 1}},
            "/bill/119/s/3270/summaries": {"summaries": [{"actionDate": "2025-11-20", "updateDate": "2025-11-21", "text": "<p>Designates a postal facility.</p>"}]},
            "/bill/119/s/3270/subjects": {"subjects": {"legislativeSubjects": [{"name": "Postal facilities"}], "policyArea": {"name": "Government Operations and Politics"}}},
            "/bill/119/s/3270/text": {"textVersions": [{"date": "2025-11-20", "formats": [{"type": "Formatted Text", "url": "https://www.congress.gov/119/bills/s3270/BILLS-119s3270is.htm"}]}]},
        }
        return Response(payloads[path])


def test_classifies_committee_and_bicameral_passage():
    status, reason = classify_status([{"text": "Committee ordered the bill reported favorably."}])
    assert status == "passed_committee"
    assert "reported" in reason
    status, _ = classify_status([{"text": "Passed House without objection."}, {"text": "Passed Senate with an amendment."}])
    assert status == "passed_both"


def test_full_sync_is_authoritative_and_idempotent(tmp_path, monkeypatch):
    db_url = f"sqlite:///{tmp_path / 'legislation-staging.db'}"
    fake = FakeHTTP()
    first = run(db_url, CongressClient("secret", delay=0, session=fake), congress=119)
    assert first["status"] == "success"
    assert first["created"] == 1

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    with Session(create_engine(db_url)) as db:
        bill = db.get(Bill, "s3270-119")
        assert bill.summary_text == "Designates a postal facility."
        assert bill.status_bucket == "passed_committee"
        assert bill.introduced_date.isoformat().startswith("2025-11-20")
        assert bill.subjects_json == ["Postal facilities"]
        assert bill.metadata_json["congress_sync"]["content_sha256"]
        assert db.query(BillAction).filter_by(bill_id="s3270-119").count() == 2
        assert db.query(MemberBillGroundTruth).filter_by(bill_id="s3270-119").count() == 2

    from sqlalchemy.orm import sessionmaker
    from routers import politics_bills
    monkeypatch.setattr(politics_bills, "SessionLocal", sessionmaker(bind=create_engine(db_url)))
    listing = politics_bills.list_bills(limit=25, offset=0, status=None, chamber=None, q=None)
    assert listing["source"] == "Congress.gov API"
    assert listing["dataset_updated_at"]
    assert listing["bills"][0]["source_retrieved_at"]
    detail = politics_bills.get_bill("s3270-119")
    assert detail["summary_source"] == "crs"
    assert detail["source_content_sha256"]
    assert detail["source_completeness"]["actions"] is True

    second_fake = FakeHTTP()
    second = run(db_url, CongressClient("secret", delay=0, session=second_fake), congress=119)
    assert second["unchanged"] == 1
    assert len(second_fake.calls) == 1
