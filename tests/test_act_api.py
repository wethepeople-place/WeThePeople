from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models.act_models import (
    ActReceipt,
    ActionCircle,
    CivicActivity,
    OfficialOfficeContact,
)
from models.auth_models import AuditLog, User
from models.database import Base, Bill, TrackedMember, get_db
from jobs.load_official_office_contacts import ContactFixtureError, load_fixture
from routers.act import router
from services.jwt_auth import get_current_user, get_optional_user


def _environment():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    app = FastAPI()
    app.include_router(router)

    def override_db():
        with Session() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    return app, TestClient(app), Session


def _seed(Session):
    with Session() as session:
        user = User(email="resident@example.test", hashed_password="test", display_name="Resident")
        other = User(email="other@example.test", hashed_password="test", display_name="Other")
        admin = User(email="admin@example.test", hashed_password="test", display_name="ACT Reviewer", role="admin")
        member = TrackedMember(
            person_id="rep-example", bioguide_id="E000001", display_name="Representative Example",
            chamber="house", state="MD", party="I", is_active=1,
        )
        other_member = TrackedMember(
            person_id="rep-other", bioguide_id="E000002", display_name="Representative Other",
            chamber="house", state="VA", party="I", is_active=1,
        )
        bill = Bill(bill_id="hr6644-119", congress=119, bill_type="hr", bill_number=6644, title="Housing bill")
        session.add_all((user, other, admin, member, other_member, bill)); session.flush()
        now = datetime.now(timezone.utc)
        session.add_all((
            OfficialOfficeContact(
                person_id=member.person_id, office_type="district", label="District office",
                phone="301-555-0100", contact_url=None, source_url="https://example.house.gov/contact",
                source_publisher="U.S. House of Representatives", verification_status="verified",
                retrieved_at=now, verified_at=now,
            ),
            OfficialOfficeContact(
                person_id=member.person_id, office_type="contact_form", label="Official contact form",
                contact_url="https://example.house.gov/contact", source_url="https://example.house.gov/contact",
                source_publisher="U.S. House of Representatives", verification_status="verified",
                retrieved_at=now, verified_at=now,
            ),
            OfficialOfficeContact(
                person_id=member.person_id, office_type="washington", label="Old office",
                phone="202-555-0199", source_url="https://example.house.gov/contact",
                source_publisher="U.S. House of Representatives", verification_status="stale",
                retrieved_at=now, verified_at=now,
            ),
        ))
        session.commit()
        return user.id, other.id


def _as_user(app, Session, user_id):
    def current_user():
        with Session() as session:
            return session.get(User, user_id)

    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_optional_user] = current_user


def test_representative_act_options_expose_only_verified_public_contacts():
    _, client, Session = _environment(); _seed(Session)
    response = client.get("/act/representatives/rep-example")
    assert response.status_code == 200
    payload = response.json()
    assert {item["label"] for item in payload["contacts"]} == {"District office", "Official contact form"}
    assert payload["fallback"]["phone"] == "202-224-3121"
    assert payload["message_policy"] == {
        "auto_send": False,
        "delivery_claimed": False,
        "instructions": "Review your message, then copy it or open the official office form. WeThePeople does not submit it for you.",
    }
    assert client.get("/act/representatives/missing").status_code == 404


def test_receipts_are_authenticated_private_idempotent_and_cannot_be_retargeted():
    app, client, Session = _environment(); user_id, other_id = _seed(Session)
    body = {
        "idempotency_key": "rep-example-message", "action_kind": "message",
        "target_type": "representative", "target_id": "rep-example",
        "representative_id": "rep-example", "status": "opened",
        "private_note": "Office form opened", "allow_aggregate": False,
    }
    assert client.put("/act/receipts/rep-example-message", json=body).status_code == 401
    _as_user(app, Session, user_id)
    first = client.put("/act/receipts/rep-example-message", json=body)
    assert first.status_code == 200
    mismatch = {**body, "idempotency_key": "rep-mismatch-message", "representative_id": "rep-other"}
    assert client.put("/act/receipts/rep-mismatch-message", json=mismatch).status_code == 422
    body["status"] = "user_confirmed_submitted"
    second = client.put("/act/receipts/rep-example-message", json=body)
    assert second.json()["id"] == first.json()["id"]
    body["representative_id"] = None
    body["target_id"] = "rep-example"
    assert client.put("/act/receipts/rep-example-message", json=body).status_code == 409
    body["representative_id"] = "rep-example"
    body["target_id"] = "different"
    assert client.put("/act/receipts/rep-example-message", json=body).status_code == 409
    assert client.get("/act/receipts").json()["items"][0]["private_note"] == "Office form opened"

    _as_user(app, Session, other_id)
    assert client.get("/act/receipts").json()["items"] == []
    with Session() as session:
        assert session.query(ActReceipt).count() == 1


def test_action_circles_are_moderated_and_membership_identity_stays_private():
    app, client, Session = _environment(); user_id, other_id = _seed(Session)
    _as_user(app, Session, user_id)
    created = client.post("/act/circles", json={
        "name": "Maryland housing call circle",
        "objective": "Ask the delegation to explain its H.R. 6644 position.",
        "description": "Residents prepare sourced questions and contact their own congressional offices.",
        "target_type": "bill", "target_id": "hr6644-119", "geography": "Maryland",
        "location_precision": "state", "membership_mode": "open",
        "conduct_rules": "Use sourced claims, respect participants, and never publish private contact details.",
        "completion_condition": "The delegation publishes or sends a documented response.",
    })
    assert created.status_code == 201 and created.json()["moderation_status"] == "pending"
    assert client.get("/act/circles").json()["items"] == []
    with Session() as session:
        circle = session.get(ActionCircle, created.json()["id"]); circle.moderation_status = "published"; session.commit()

    _as_user(app, Session, other_id)
    joined = client.put(f"/act/circles/{created.json()['id']}/membership")
    assert joined.json() == {"status": "active", "member_count_is_public": True, "member_identity_is_public": False}
    public = client.get("/act/circles").json()["items"][0]
    assert public["member_count"] == 2 and "members" not in public


def test_activities_are_moderated_capacity_bounded_and_legal_actions_stay_disabled():
    app, client, Session = _environment(); user_id, other_id = _seed(Session)
    _as_user(app, Session, user_id)
    future = datetime.now(timezone.utc) + timedelta(days=2)
    created = client.post("/act/activities", json={
        "title": "Constituent call preparation",
        "description": "Prepare sourced questions before calling each participant's own office.",
        "host_type": "community", "format": "online", "starts_at": future.isoformat(),
        "timezone": "America/New_York", "public_url": "https://example.org/activity", "capacity": 1,
    })
    assert created.status_code == 201 and client.get("/act/activities").json()["items"] == []
    with Session() as session:
        activity = session.get(CivicActivity, created.json()["id"]); activity.moderation_status = "published"; session.commit()
    _as_user(app, Session, other_id)
    assert client.put(f"/act/activities/{created.json()['id']}/rsvp").json()["attendee_identity_is_public"] is False
    _as_user(app, Session, user_id)
    assert client.put(f"/act/activities/{created.json()['id']}/rsvp").status_code == 409
    _as_user(app, Session, other_id)
    assert client.delete(f"/act/activities/{created.json()['id']}/rsvp").status_code == 204
    _as_user(app, Session, user_id)
    assert client.put(f"/act/activities/{created.json()['id']}/rsvp").status_code == 200
    _as_user(app, Session, other_id)
    assert client.put(f"/act/activities/{created.json()['id']}/rsvp").status_code == 409
    assert client.get("/act/legal-pathways").json()["enabled"] is False
    assert client.get("/act/petitions").json()["enabled"] is False


def test_reviewed_contact_loader_is_idempotent_and_rejects_nonofficial_sources():
    _, _, Session = _environment(); _seed(Session)
    now = datetime.now(timezone.utc).isoformat()
    payload = {"schema_version": 1, "contacts": [{
        "person_id": "rep-example", "office_type": "district", "label": "District office",
        "phone": "301-555-0100", "contact_url": "https://example.house.gov/contact",
        "source_url": "https://example.house.gov/contact", "source_publisher": "U.S. House of Representatives",
        "retrieved_at": now, "verified_at": now,
    }]}
    with Session() as session:
        assert load_fixture(payload, session) == {"verified_contacts": 1, "members": 1}
        assert load_fixture(payload, session) == {"verified_contacts": 1, "members": 1}
        assert session.query(OfficialOfficeContact).filter_by(person_id="rep-example", office_type="district").count() == 1
        hostile = {"schema_version": 1, "contacts": [{**payload["contacts"][0], "source_url": "https://not-official.example/contact"}]}
        try:
            load_fixture(hostile, session)
            assert False, "nonofficial source must fail"
        except ContactFixtureError:
            pass


def test_act_moderation_is_admin_only_transition_safe_and_audited():
    app, client, Session = _environment(); user_id, _ = _seed(Session)
    future = datetime.now(timezone.utc) + timedelta(days=3)
    with Session() as session:
        circle = ActionCircle(
            organizer_id=user_id, name="Housing evidence circle",
            objective="Ask representatives to respond to sourced housing evidence.",
            description="Residents prepare respectful questions tied to public legislative records.",
            target_type="bill", target_id="hr6644-119", location_precision="none",
            membership_mode="approval", conduct_rules="Use public evidence and never expose private contact details.",
            completion_condition="A documented official response is received.", moderation_status="pending",
        )
        session.add(circle); session.flush()
        activity = CivicActivity(
            organizer_id=user_id, circle_id=circle.id, title="Housing evidence preparation",
            description="Review public evidence before constituents contact their own offices.",
            host_type="community", format="online", starts_at=future,
            timezone="America/New_York", public_url="https://example.org/event", moderation_status="pending",
        )
        session.add(activity); session.commit(); circle_id, activity_id = circle.id, activity.id

    assert client.get("/act/admin/moderation").status_code == 401
    _as_user(app, Session, user_id)
    assert client.get("/act/admin/moderation").status_code == 403
    with Session() as session:
        admin_id = session.query(User).filter_by(email="admin@example.test").one().id
    _as_user(app, Session, admin_id)
    queue = client.get("/act/admin/moderation").json()
    assert queue["counts"] == {"circles": 1, "activities": 1}
    assert {item["organizer"]["display_name"] for item in queue["items"]} == {"Resident"}
    assert all("members" not in item and "attendees" not in item for item in queue["items"])

    blocked = client.patch(f"/act/admin/activities/{activity_id}", json={"status": "published", "reason": "Reviewed and safe to publish."})
    assert blocked.status_code == 409
    published_circle = client.patch(f"/act/admin/circles/{circle_id}", json={"status": "published", "reason": "Objective and conduct rules are specific and safe."})
    assert published_circle.status_code == 200
    published_activity = client.patch(f"/act/admin/activities/{activity_id}", json={"status": "published", "reason": "Future public event with a safe HTTPS destination."})
    assert published_activity.status_code == 200
    assert client.patch(f"/act/admin/circles/{circle_id}", json={"status": "pending", "reason": "Invalid reverse transition attempt."}).status_code == 409
    with Session() as session:
        logs = session.query(AuditLog).filter(AuditLog.action.in_(("act_circle_moderated", "act_activity_moderated"))).all()
        assert len(logs) == 2 and all(log.user_id == admin_id for log in logs)
