"""Truthful, deterministic connections from reviewed Agenda topics to canonical data."""

from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from jobs.load_agenda_priorities import AGENDA_FIXTURE_PATH, validate_fixture
from models.database import Bill


@dataclass(frozen=True)
class BillRule:
    policy_areas: tuple[str, ...]
    title_terms: tuple[str, ...] = ()


# Congress.gov assigns one official policy area to each bill. Broad Agenda topics
# may intentionally share an official policy area; title terms narrow only the
# topics whose names are more specific than Congress.gov's taxonomy.
BILL_RULES: dict[str, BillRule] = {
    "climate-environment": BillRule(("Environmental Protection", "Energy", "Public Lands and Natural Resources")),
    "cost-of-living": BillRule(("Economics and Public Finance", "Commerce"), ("cost", "price", "afford", "consumer")),
    "crime-violence": BillRule(("Crime and Law Enforcement",)),
    "economy": BillRule(("Economics and Public Finance", "Commerce", "Finance and Financial Sector")),
    "education-student-debt": BillRule(("Education",)),
    "federal-budget-debt": BillRule(("Economics and Public Finance", "Government Operations and Politics"), ("budget", "debt", "deficit", "appropriat", "spending")),
    "food-costs-security": BillRule(("Agriculture and Food",)),
    "government-corruption": BillRule(("Government Operations and Politics", "Congress"), ("ethic", "fraud", "corrupt", "accountab", "inspect", "transparen")),
    "health-care-costs": BillRule(("Health",), ("cost", "price", "insurance", "medicare", "medicaid", "drug")),
    "health-care-reform": BillRule(("Health",)),
    "housing-rent": BillRule(("Housing and Community Development",)),
    "immigration": BillRule(("Immigration",)),
    "inflation": BillRule(("Economics and Public Finance",), ("inflation", "price", "purchasing power")),
    "jobs-unemployment": BillRule(("Labor and Employment",), ("job", "employ", "unemploy", "workforce")),
    "poverty-hunger-homelessness": BillRule(("Social Welfare", "Agriculture and Food", "Housing and Community Development"), ("poverty", "hunger", "homeless", "food security", "nutrition assistance")),
    "social-security": BillRule(("Social Welfare",), ("social security", "old-age", "disability insurance", "oasdi")),
    "taxes": BillRule(("Taxation",)),
    "trade-tariffs": BillRule(("Foreign Trade and International Finance",)),
    "wages": BillRule(("Labor and Employment",), ("wage", "pay", "salary", "compensation")),
    "welfare-entitlements": BillRule(("Social Welfare",)),
}


def agenda_payload() -> dict:
    payload = json.loads(AGENDA_FIXTURE_PATH.read_text(encoding="utf-8"))
    validate_fixture(payload)
    return payload


def agenda_priority_series(slug: str) -> dict | None:
    """Expose the reviewed AP-NORC priority observation already backing Agenda."""
    payload = agenda_payload()
    item = next((row for row in payload["items"] if row["slug"] == slug), None)
    if item is None:
        return None
    methodology = payload["methodology"]
    source = {
        "url": methodology["source_url"],
        "publisher": methodology["publisher"],
        "retrieved_at": methodology["retrieved_at"],
    }
    observation = {
        "date": methodology["survey_end"],
        "value": item["priority_share"],
        "source_record_id": f"apnorc-2026-priority-{slug}",
        "source": source,
    }
    return {
        "key": "apnorc-2026-public-priority-share",
        "title": f"Adults naming {item['title']} as a 2026 government priority",
        "unit": "percent of U.S. adults",
        "geography": {"type": "national", "id": "US"},
        "source": source,
        "observations": [observation],
    }


def matched_bills_query(db: Session, slug: str) -> Query:
    rule = BILL_RULES.get(slug)
    if rule is None:
        return db.query(Bill).filter(False)
    query = db.query(Bill).filter(Bill.policy_area.in_(rule.policy_areas))
    if rule.title_terms:
        title_filters = [Bill.title.ilike(f"%{term}%") for term in rule.title_terms]
        query = query.filter(or_(*title_filters))
    return query


def bill_match_note(slug: str, bill: Bill) -> str:
    rule = BILL_RULES[slug]
    if rule.title_terms:
        return (
            f"Automatically connected from Congress.gov policy area “{bill.policy_area}” "
            "and a topic-specific title match; not an editorial endorsement."
        )
    return (
        f"Automatically connected from the official Congress.gov policy area “{bill.policy_area}”; "
        "not an editorial endorsement."
    )
