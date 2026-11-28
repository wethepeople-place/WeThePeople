"""Smoke and contract tests for politics router endpoints."""

from datetime import datetime, timezone


def test_politics_dashboard_stats(client):
    """Dashboard stats should return 200 even with empty DB."""
    r = client.get("/politics/dashboard/stats")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)


def test_politics_people_list(client):
    """People list should return 200 with empty results."""
    r = client.get("/politics/people")
    # May return 200 with empty list or 404 — both are acceptable
    assert r.status_code in (200, 404)


def test_compare_uses_official_legislative_records(db_session, monkeypatch):
    """Compare should expose source-backed metrics and honest coverage state."""
    from sqlalchemy.orm import sessionmaker

    import routers.politics_people as politics_people
    from models.committee_models import Committee, CommitteeMembership
    from models.database import Action, Bill, MemberVote, TrackedMember, Vote

    senator = (
        db_session.query(TrackedMember)
        .filter(TrackedMember.person_id == "test-senator")
        .one()
    )
    senator.last_full_refresh_at = datetime.now(timezone.utc)
    senator.needs_ingest = 0

    representative = TrackedMember(
        person_id="test-representative",
        display_name="Test Representative",
        bioguide_id="T000002",
        state="OH",
        party="R",
        chamber="house",
        is_active=1,
        last_full_refresh_at=datetime.now(timezone.utc),
        needs_ingest=0,
    )
    db_session.add(representative)

    bill = Bill(
        bill_id="s42-119",
        congress=119,
        bill_type="s",
        bill_number=42,
        title="Test enacted bill",
        status_bucket="enacted",
    )
    db_session.add(bill)
    db_session.add(Action(
        person_id="test-senator",
        title="Sponsored S. 42",
        action_type="Sponsored",
        bill_congress=119,
        bill_type="s",
        bill_number=42,
        policy_area="Health",
    ))

    vote_one = Vote(congress=119, chamber="senate", roll_number=9001)
    vote_two = Vote(congress=119, chamber="senate", roll_number=9002)
    db_session.add_all([vote_one, vote_two])
    db_session.flush()
    db_session.add_all([
        MemberVote(vote_id=vote_one.id, bioguide_id="T000001", person_id="test-senator", party="D", position="Yea"),
        MemberVote(vote_id=vote_one.id, bioguide_id="D000002", party="D", position="Yea"),
        MemberVote(vote_id=vote_one.id, bioguide_id="R000001", party="R", position="Nay"),
        MemberVote(vote_id=vote_two.id, bioguide_id="T000001", person_id="test-senator", party="D", position="Nay"),
        MemberVote(vote_id=vote_two.id, bioguide_id="D000002", party="D", position="Yea"),
        MemberVote(vote_id=vote_two.id, bioguide_id="D000003", party="D", position="Yea"),
        MemberVote(vote_id=vote_two.id, bioguide_id="R000001", party="R", position="Nay"),
    ])

    committee = Committee(
        thomas_id="TST1",
        name="Test Committee",
        chamber="senate",
        committee_type="standing",
    )
    db_session.add(committee)
    db_session.add(CommitteeMembership(
        committee_thomas_id="TST1",
        bioguide_id="T000001",
        person_id="test-senator",
        role="chair",
    ))
    db_session.commit()

    monkeypatch.setattr(
        politics_people,
        "SessionLocal",
        sessionmaker(bind=db_session.get_bind()),
    )
    payload = politics_people.get_comparison("test-senator,test-representative")
    assert payload["comparison_count"] == 2
    assert payload["coverage"] == {"available": 1, "partial": 1, "not_loaded": 0}
    assert payload["sources"]["bills"] == "https://api.congress.gov/"

    by_id = {person["person_id"]: person for person in payload["people"]}
    compared = by_id["test-senator"]
    assert compared["sponsored_bills"] == 1
    assert compared["enacted_bills"] == 1
    assert compared["total_votes"] == 2
    assert compared["vote_positions"] == {"yes": 1, "no": 1}
    assert compared["party_alignment_rate"] == 50.0
    assert compared["cross_party_votes"] == 1
    assert compared["committee_count"] == 1
    assert compared["committee_leadership_roles"] == 1
    assert compared["data_status"] == "available"

    not_loaded = by_id["test-representative"]
    assert not_loaded["action_data_available"] is True
    assert not_loaded["vote_data_available"] is False
    assert not_loaded["committee_data_available"] is False
    assert not_loaded["data_status"] == "partial"


def test_people_uses_bioguide_photo_fallback():
    from routers.politics_people import _official_bioguide_photo_url

    assert _official_bioguide_photo_url("T000001") == (
        "https://bioguide.congress.gov/bioguide/photo/T/T000001.jpg"
    )


def test_member_action_sync_marks_coverage_only_after_complete_fetch(db_session, monkeypatch):
    from sqlalchemy.orm import sessionmaker

    import connectors.congress as congress
    from models.database import TrackedMember

    db_session.add_all([
        TrackedMember(
            person_id="sync-good-member",
            display_name="A Good Member",
            bioguide_id="G000001",
            state="MD",
            party="D",
            chamber="house",
            is_active=1,
            needs_ingest=1,
        ),
        TrackedMember(
            person_id="sync-failed-member",
            display_name="B Failed Member",
            bioguide_id="F000001",
            state="VA",
            party="R",
            chamber="house",
            is_active=1,
            needs_ingest=1,
        ),
    ])
    db_session.commit()

    monkeypatch.setattr(congress, "SessionLocal", sessionmaker(bind=db_session.get_bind()))
    monkeypatch.setattr(congress, "fetch_member_sponsored", lambda *_args: [])

    def fetch_cosponsored(bioguide_id, _limit_pages):
        if bioguide_id == "F000001":
            raise RuntimeError("upstream unavailable")
        return []

    monkeypatch.setattr(congress, "fetch_member_cosponsored", fetch_cosponsored)
    result = congress.ingest_member_legislation(
        person_ids=["sync-good-member", "sync-failed-member"],
        limit_pages=1,
    )

    assert result == {
        "selected_members": 2,
        "processed_members": 1,
        "failed_members": 1,
        "new_actions": 0,
    }
    db_session.expire_all()
    good = db_session.query(TrackedMember).filter_by(person_id="sync-good-member").one()
    failed = db_session.query(TrackedMember).filter_by(person_id="sync-failed-member").one()
    assert good.last_full_refresh_at is not None
    assert good.needs_ingest == 0
    assert failed.last_full_refresh_at is None
    assert failed.needs_ingest == 1


def test_congress_pagination_failure_is_not_silently_treated_as_complete(monkeypatch):
    import pytest

    import connectors.congress as congress

    class FailedResponse:
        status_code = 503

    monkeypatch.setattr(congress, "robust_get", lambda *_args, **_kwargs: FailedResponse())
    with pytest.raises(RuntimeError, match="pagination failed"):
        congress.fetch_paged("https://api.congress.gov/v3/member/test", "bills")
