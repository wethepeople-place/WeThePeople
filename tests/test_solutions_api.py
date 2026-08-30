from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models.auth_models import User
from models.civic_models import Proposal, SolutionRevision, SolutionVote
from models.database import Base, get_db
from models.issue_models import Issue
from routers.solutions import VOTE_RULE, router
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
    with Session() as session:
        session.add(Issue(slug="housing-rent", title="Housing & Rent"))
        session.add_all([
            User(email="alice@example.test", hashed_password="test", display_name="Alice"),
            User(email="bob@example.test", hashed_password="test", display_name="Bob"),
        ])
        session.commit()
        users = {user.email: user.id for user in session.query(User).all()}
    return app, TestClient(app), Session, users


def _as_user(app, Session, user_id):
    def current_user():
        with Session() as session:
            return session.get(User, user_id)
    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_optional_user] = current_user


def _payload():
    return {
        "issue_slug": "housing-rent",
        "title": "Expand housing supply near frequent transit",
        "summary": "Tie a bounded federal incentive to locally approved housing near frequent transit.",
        "body": "Create a time-limited incentive with public eligibility rules, annual reporting, and an independent evaluation.",
    }


def test_solution_submission_is_canonical_issue_linked_and_revisioned():
    app, client, Session, users = _environment()
    assert client.post("/solutions", json=_payload()).status_code == 401
    _as_user(app, Session, users["alice@example.test"])
    created = client.post("/solutions", json=_payload())
    assert created.status_code == 201
    item = created.json()
    assert item["creator_user_id"] == users["alice@example.test"]
    assert item["issue_slug"] == "housing-rent" and item["status"] == "published"
    assert item["vote_totals"] == {"support": 0, "oppose": 0, "total_ballots": 0}
    assert item["vote_rule"] == VOTE_RULE and item["vote_choices"] == ["support", "oppose"]
    assert item["discussion_post_id"] is not None
    with Session() as session:
        assert session.query(SolutionRevision).filter_by(solution_id=item["id"]).one().change_note == "Initial publication"
        assert session.get(Proposal, item["id"]).author_id == users["alice@example.test"]


def test_solution_can_attach_a_normalized_consent_gated_provider_video():
    app, client, Session, users = _environment()
    _as_user(app, Session, users["alice@example.test"])
    payload = {**_payload(), "video_url": "https://www.youtube.com/shorts/ssTeslcxXbY"}
    created = client.post("/solutions", json=payload)
    assert created.status_code == 201
    item = created.json()
    assert item["video_link"] == {
        "provider": "youtube",
        "provider_video_id": "ssTeslcxXbY",
        "canonical_url": "https://www.youtube.com/watch?v=ssTeslcxXbY",
    }
    assert item["discussion_post_id"] is not None
    from models.social_models import DiscussionAttachment, DiscussionPost
    with Session() as session:
        post = session.get(DiscussionPost, item["discussion_post_id"])
        assert post.moderation_status == "published"
        assert {(link.attachment_type, link.issue_slug, link.solution_id) for link in post.attachments} == {
            ("issue", "housing-rent", None), ("solution", None, item["id"]),
        }


def test_solution_list_is_issue_scoped_public_and_not_hot_ranked():
    app, client, Session, users = _environment()
    _as_user(app, Session, users["alice@example.test"])
    created = client.post("/solutions", json=_payload()).json()
    solution_id = created["id"]
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_optional_user, None)
    feed = client.get("/solutions?issue_slug=housing-rent").json()
    assert feed["total"] == 1 and feed["items"][0]["id"] == solution_id
    assert "hot_score" not in feed["items"][0] and "confidence_score" not in feed["items"][0]
    assert client.get(f"/solutions/{solution_id}").json()["current_user_choice"] is None
    assert client.get("/solutions?issue_slug=other").json()["items"] == []


def test_vote_is_equal_weight_idempotent_changeable_removable_and_private():
    app, client, Session, users = _environment()
    _as_user(app, Session, users["alice@example.test"])
    created = client.post("/solutions", json=_payload()).json()
    solution_id = created["id"]
    first = client.put(f"/solutions/{solution_id}/vote", json={"choice": "support"}).json()
    second = client.put(f"/solutions/{solution_id}/vote", json={"choice": "support"}).json()
    assert first["vote_totals"] == second["vote_totals"] == {"support": 1, "oppose": 0, "total_ballots": 1}
    changed = client.put(f"/solutions/{solution_id}/vote", json={"choice": "oppose"}).json()
    assert changed["vote_totals"] == {"support": 0, "oppose": 1, "total_ballots": 1}
    assert "voter" not in str(client.get(f"/solutions/{solution_id}").json()).lower()
    removed = client.put(f"/solutions/{solution_id}/vote", json={"choice": None}).json()
    assert removed["vote_totals"]["total_ballots"] == 0
    with Session() as session:
        assert session.query(SolutionVote).count() == 0


def test_only_creator_can_revise_and_history_is_append_only():
    app, client, Session, users = _environment()
    _as_user(app, Session, users["alice@example.test"])
    solution_id = client.post("/solutions", json=_payload()).json()["id"]
    edit = {**_payload(), "title": "Revised housing supply incentive", "change_note": "Clarified the evaluation rule"}
    edit.pop("issue_slug")
    revised = client.put(f"/solutions/{solution_id}", json=edit)
    assert revised.status_code == 200 and revised.json()["latest_revision_number"] == 2
    _as_user(app, Session, users["bob@example.test"])
    assert client.put(f"/solutions/{solution_id}", json=edit).status_code == 403
    with Session() as session:
        history = session.query(SolutionRevision).filter_by(solution_id=solution_id).order_by(SolutionRevision.revision_number).all()
        assert [row.revision_number for row in history] == [1, 2]
        assert history[0].title != history[1].title
    revisions = client.get(f"/solutions/{solution_id}/revisions").json()
    assert [item["revision_number"] for item in revisions["items"]] == [2, 1]
    assert revisions["items"][0]["change_note"] == "Clarified the evaluation rule"
    assert revisions["items"][0]["editor_display_name"] == "Alice"


def test_solution_vote_constraints_enforce_relational_contract():
    app, client, Session, users = _environment()
    _as_user(app, Session, users["alice@example.test"])
    solution_id = client.post("/solutions", json=_payload()).json()["id"]
    with Session() as session:
        session.add(SolutionVote(solution_id=solution_id, voter_user_id=users["alice@example.test"], choice="maybe"))
        try:
            session.commit()
            assert False, "invalid choice must fail"
        except IntegrityError:
            session.rollback()
        session.add_all([
            SolutionVote(solution_id=solution_id, voter_user_id=users["alice@example.test"], choice="support"),
            SolutionVote(solution_id=solution_id, voter_user_id=users["alice@example.test"], choice="oppose"),
        ])
        try:
            session.commit()
            assert False, "duplicate current vote must fail"
        except IntegrityError:
            session.rollback()


def test_solution_detail_rejects_issue_mismatch_and_exposes_normalized_discussion():
    app, client, Session, users = _environment()
    _as_user(app, Session, users["alice@example.test"])
    created = client.post("/solutions", json=_payload()).json()
    solution_id = created["id"]
    from models.social_models import DiscussionAttachment, DiscussionPost
    with Session() as session:
        post = DiscussionPost(author_label="WeThePeople.place", body="Sourced Housing discussion")
        session.add(post); session.flush()
        session.add(DiscussionAttachment(post_id=post.id, attachment_type="solution", solution_id=solution_id, label="Housing solution"))
        session.commit(); post_id = post.id
    assert client.get(f"/solutions/{solution_id}?issue_slug=other").status_code == 404
    detail = client.get(f"/solutions/{solution_id}?issue_slug=housing-rent").json()
    assert detail["discussion_post_id"] == created["discussion_post_id"] and detail["discussion_post_id"] != post_id
    assert detail["creator_display_name"] == "Alice"
    assert "moderation_reason" not in detail


def test_duplicate_removed_closed_and_private_states_are_bounded():
    app, client, Session, users = _environment()
    _as_user(app, Session, users["alice@example.test"])
    canonical_id = client.post("/solutions", json=_payload()).json()["id"]
    with Session() as session:
        duplicate = Proposal(author_id=users["alice@example.test"], issue_slug="housing-rent", title="Duplicate title", summary="Duplicate summary text", body="Private duplicate body text that must not leak.", status="duplicate", duplicate_of_id=canonical_id, moderation_reason="Private duplicate note")
        removed = Proposal(author_id=users["alice@example.test"], issue_slug="housing-rent", title="Removed title", summary="Removed summary text", body="Private removed body text that must not leak.", status="removed", moderation_reason="Private removal note")
        draft = Proposal(author_id=users["alice@example.test"], issue_slug="housing-rent", title="Draft title", summary="Draft summary text", body="Private draft body text that must not leak.", status="draft")
        session.add_all([duplicate, removed, draft]); session.commit()
        duplicate_id, removed_id, draft_id = duplicate.id, removed.id, draft.id
        session.get(Proposal, canonical_id).status = "closed"; session.commit()
    duplicate_payload = client.get(f"/solutions/{duplicate_id}").json()
    assert duplicate_payload["duplicate_of_solution_id"] == canonical_id and "Private" not in str(duplicate_payload)
    removed_payload = client.get(f"/solutions/{removed_id}").json()
    assert removed_payload == {"id": removed_id, "issue_slug": "housing-rent", "status": "removed", "message": "This solution was removed."}
    assert client.get(f"/solutions/{draft_id}").status_code == 404
    assert client.put(f"/solutions/{canonical_id}/vote", json={"choice": "support"}).status_code == 409
    assert client.put(f"/solutions/{duplicate_id}", json={"title": "Still duplicate", "summary": "Still duplicate summary", "body": "Still duplicate body with enough text", "change_note": "No change"}).status_code == 409
