import json
from unittest.mock import patch

from jobs.load_agenda_priorities import AGENDA_FIXTURE_PATH, load_fixture
from models.database import Bill
from services.issue_connections import BILL_RULES
from tests.test_housing_rent_api import _client


def test_every_reviewed_agenda_topic_has_sourced_priority_evidence_and_bill_rule():
    client, Session = _client()
    payload = json.loads(AGENDA_FIXTURE_PATH.read_text(encoding="utf-8"))
    with Session() as session:
        load_fixture(payload, session)
        for index, item in enumerate(payload["items"], start=1):
            rule = BILL_RULES[item["slug"]]
            session.add(Bill(
                bill_id=f"hr{index}-119",
                congress=119,
                bill_type="hr",
                bill_number=index,
                title=(rule.title_terms[0] if rule.title_terms else item["title"]) + " Act",
                policy_area=rule.policy_areas[0],
            ))
        session.commit()

    for item in payload["items"]:
        slug = item["slug"]
        evidence = client.get(f"/issues/{slug}/evidence").json()
        assert evidence["total"] >= 1
        priority = evidence["series"][0]
        assert priority["key"] == "apnorc-2026-public-priority-share"
        assert priority["observations"][0]["value"] == item["priority_share"]
        assert priority["source"]["url"].startswith("https://apnorc.org/")

        bills = client.get(f"/issues/{slug}/bills").json()
        assert bills["total"] >= 1
        assert bills["bills"]
        assert all(row["source"]["url"].startswith("https://") for row in bills["bills"])
        automatic = [row for row in bills["bills"] if row["source"]["publisher"] == "Congress.gov"]
        assert automatic
        assert all("not an editorial endorsement" in (row["relevance_note"] or "") for row in automatic)


def test_usajobs_is_bounded_to_jobs_topic_and_keeps_official_source_label():
    client, Session = _client()
    payload = json.loads(AGENDA_FIXTURE_PATH.read_text(encoding="utf-8"))
    with Session() as session:
        load_fixture(payload, session)

    result = {
        "total": 1,
        "jobs": [{
            "position_title": "Program Analyst",
            "organization_name": "Department of Labor",
            "department_name": "Department of Labor",
            "salary_min": "80000",
            "salary_max": "110000",
            "location": "Washington, DC",
            "grade": "13",
            "schedule_type": "Full-time",
            "start_date": "2026-08-30",
            "end_date": "2026-09-15",
            "url": "https://www.usajobs.gov/job/123",
        }],
    }
    with patch("routers.issues.search_jobs", return_value=result):
        response = client.get("/issues/jobs-unemployment/federal-jobs")
    assert response.status_code == 200
    assert response.json()["source"]["publisher"] == "USAJOBS"
    assert response.json()["jobs"][0]["url"].startswith("https://www.usajobs.gov/")
    assert client.get("/issues/immigration/federal-jobs").status_code == 404
