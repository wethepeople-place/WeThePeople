"""Prove the canonical Housing & Rent journey in one disposable database."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from jobs.load_discuss_fixture import load_fixture as load_discuss
from jobs.load_housing_rent_slice import load_fixture as load_housing
from jobs.load_solution_fixture import load_fixture as load_solution
from jobs.load_watch_fixture import load_fixture as load_watch
from models.auth_models import User
from models.database import Base, TrackedMember, get_db
from routers.discussions import router as discussions_router
from routers.issues import router as issues_router
from routers.lookup import router as lookup_router
from routers.solutions import router as solutions_router
from routers.videos import router as videos_router
from tests.test_discussions_api import _discuss_fixture
from tests.test_housing_rent_loader import _fixture as housing_fixture
from tests.test_solution_fixture import _fixture as solution_fixture
from tests.test_watch_slice import _watch_fixture


def test_watch_to_evidence_to_government_to_discuss_to_solution():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    app = FastAPI()
    for router in (issues_router, videos_router, discussions_router, solutions_router, lookup_router):
        app.include_router(router)

    def override_db():
        with Session() as session:
            yield session

    app.dependency_overrides[get_db] = override_db

    with Session() as session:
        load_housing(housing_fixture(), session)
        load_watch(_watch_fixture(), session)
        load_discuss(_discuss_fixture(), session)
        editor = User(
            email="journey-editor@example.test",
            hashed_password="test-only",
            display_name="Journey editor",
        )
        session.add(editor)
        session.commit()
        load_solution(solution_fixture(), session, editor.id)
        session.add_all([
            TrackedMember(person_id="bill_huizenga", bioguide_id="H001058", display_name="Bill Huizenga", chamber="house", state="MI", party="R", is_active=1),
            TrackedMember(person_id="elissa_slotkin", bioguide_id="S001208", display_name="Elissa Slotkin", chamber="senate", state="MI", party="D", is_active=1),
            TrackedMember(person_id="gary_c_peters", bioguide_id="P000595", display_name="Gary C. Peters", chamber="senate", state="MI", party="D", is_active=1),
        ])
        session.commit()

    client = TestClient(app)

    issue = client.get("/issues/housing-rent")
    assert issue.status_code == 200
    assert issue.json()["slug"] == "housing-rent"

    evidence = client.get("/issues/housing-rent/evidence").json()
    assert len(evidence["series"]) == 4
    assert evidence["series"][0]["key"] == "apnorc-2026-public-priority-share"
    assert all(series["source"]["url"].startswith("https://") for series in evidence["series"])

    government = client.get("/issues/housing-rent/bills").json()
    assert len(government["bills"]) == 7
    assert any(item["bill_id"] == "hr1-119" for item in government["bills"])

    watch = client.get("/videos").json()
    assert watch["total"] == 1
    video = watch["videos"][0]
    assert video["issue"]["slug"] == "housing-rent"
    assert video["discussion_post_id"] is not None

    discuss = client.get("/discussions").json()
    assert discuss["total"] == 1
    post = discuss["items"][0]
    assert {item["type"] for item in post["attachments"]} == {
        "bill", "issue", "solution", "source", "video",
    }

    solutions = client.get("/solutions", params={"issue_slug": "housing-rent"}).json()
    assert solutions["total"] == 1
    solution = solutions["items"][0]
    assert solution["discussion_post_id"] == post["id"]
    assert solution["latest_revision_number"] == 1

    revisions = client.get(f"/solutions/{solution['id']}/revisions").json()
    assert revisions["latest_revision_number"] == 1
    assert len(revisions["items"]) == 1

    action = client.get("/lookup/49001").json()
    assert action["state"] == "MI"
    assert {(item["person_id"], item["chamber"]) for item in action["representatives"]} == {
        ("bill_huizenga", "house"),
        ("elissa_slotkin", "senate"),
        ("gary_c_peters", "senate"),
    }
