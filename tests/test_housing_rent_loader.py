from copy import deepcopy

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from jobs.housing_rent_contract import CURATED_BILLS, EVIDENCE_SERIES
from jobs.load_housing_rent_slice import SliceValidationError, load_fixture
from models.database import Base, MemberBillGroundTruth, SourceDocument
from models.issue_models import BillCommitteeReferral, EvidenceObservation, IssueBill


def _fixture():
    retrieved_at = "2026-07-31T00:00:00Z"
    hud_url = "https://www.huduser.gov/portal/dataset/fmr-api.html"
    bls_url = "https://www.bls.gov/developers/"
    congress_base = "https://www.congress.gov/bill/119th-congress"
    congress_urls = {
        spec.bill_id: f"{congress_base}/{'house-bill' if spec.bill_type == 'hr' else 'senate-bill'}/{spec.bill_number}"
        for spec in CURATED_BILLS
    }
    sources = [
        {"url": hud_url, "publisher": "HUD", "retrieved_at": retrieved_at},
        {"url": bls_url, "publisher": "BLS", "retrieved_at": retrieved_at},
        *[
            {"url": url, "publisher": "Congress.gov", "retrieved_at": retrieved_at}
            for url in congress_urls.values()
        ],
    ]
    series = []
    for spec in EVIDENCE_SERIES:
        source_url = hud_url if spec.key == "median_rent" else bls_url
        series.append(
            {
                "key": spec.key,
                "title": spec.key.replace("_", " ").title(),
                "unit": "USD",
                "source_url": source_url,
                "observations": [
                    {
                        "date": "2025-01-01",
                        "value": 100.0,
                        "source_record_id": f"{spec.key}-2025",
                    }
                ],
            }
        )
    bills = []
    for index, spec in enumerate(CURATED_BILLS):
        item = {
            "bill_id": spec.bill_id,
            "title": f"Fixture bill {spec.bill_id}",
            "status_bucket": "introduced",
            "phase": "upcoming",
            "source_url": congress_urls[spec.bill_id],
            "people": [],
            "committee_referrals": [],
        }
        if index == 0:
            item["people"] = [{"bioguide_id": "H001058", "role": "sponsor"}]
            item["committee_referrals"] = [
                {
                    "thomas_id": "HSBA",
                    "name": "House Committee on Financial Services",
                    "chamber": "house",
                    "official_url": "https://financialservices.house.gov/",
                    "referred_at": "2025-01-03",
                    "action_date": "2025-01-03T00:00:00Z",
                    "action_text": "Referred to the Committee on Financial Services.",
                    "source_url": congress_urls[spec.bill_id],
                }
            ]
        bills.append(item)
    return {
        "issue": {"slug": "housing-rent", "title": "Housing & Rent"},
        "sources": sources,
        "evidence_series": series,
        "bills": bills,
    }


def test_loader_is_idempotent_and_preserves_normalized_provenance(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'loader.db'}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    payload = _fixture()

    with Session() as session:
        first = load_fixture(payload, session)
        second = load_fixture(payload, session)

        assert first == second == {
            "issues": 1,
            "evidence_series": 2,
            "evidence_observations": 2,
            "issue_bills": 7,
        }
        assert session.query(SourceDocument).count() == 9
        assert session.query(EvidenceObservation).count() == 2
        assert session.query(IssueBill).count() == 7
        assert session.query(MemberBillGroundTruth).count() == 1
        assert session.query(BillCommitteeReferral).count() == 1
        assert session.query(IssueBill).first().source.retrieved_at is not None


def test_loader_rejects_scope_expansion_before_writing(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'reject.db'}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    payload = deepcopy(_fixture())
    payload["bills"].append(
        {
            "bill_id": "hr9999-119",
            "title": "Unreviewed",
            "status_bucket": "introduced",
            "phase": "upcoming",
            "source_url": payload["sources"][2]["url"],
        }
    )

    with Session() as session:
        with pytest.raises(SliceValidationError, match="exactly the seven reviewed bills"):
            load_fixture(payload, session)
        assert session.query(IssueBill).count() == 0
