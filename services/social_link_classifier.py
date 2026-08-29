"""Bounded metadata retrieval and deterministic Agenda matching for social links."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Iterable

import requests
from bs4 import BeautifulSoup


METADATA_TIMEOUT = (2, 5)
MAX_METADATA_BYTES = 300_000
USER_AGENT = "WeThePeople-LinkClassifier/1.0 (+https://app.wethepeople.place)"


ISSUE_TERMS: dict[str, tuple[str, ...]] = {
    "immigration": ("immigration", "immigrant", "border", "daca", "deport", "ice raid", "asylum"),
    "economy": ("economy", "economic", "recession", "gdp", "consumer confidence"),
    "health-care-reform": ("universal healthcare", "universalhealthcare", "universal health care", "health care reform", "healthcare reform", "health insurance", "healthinsurance", "medical coverage", "medicaid expansion", "medicare for all", "uninsured", "chronicillness"),
    "cost-of-living": ("cost of living", "affordability", "household budget", "living expenses"),
    "inflation": ("inflation", "rising prices", "price increases", "purchasing power"),
    "housing-rent": ("housing", "rent", "renter", "landlord", "mortgage", "home price", "foreclosure", "eviction"),
    "education-student-debt": ("education", "school", "teacher", "college", "university", "student loan", "student debt", "tuition"),
    "jobs-unemployment": ("unemployment", "job market", "job loss", "layoff", "hiring", "employment"),
    "poverty-hunger-homelessness": ("poverty", "homeless", "hunger", "food insecurity", "shelter"),
    "taxes": ("tax reform", "income tax", "corporate tax", "tax cut", "tax rate", "taxes"),
    "climate-environment": ("climate", "environment", "pollution", "emissions", "global warming", "clean energy"),
    "crime-violence": (
        "crime",
        "violence",
        "shooting",
        "public safety",
        "hate crime",
        "gun violence",
        "criminal law",
        "drug policy",
        "controlled substance",
        "marijuana",
        "cannabis",
        "hemp",
        "thc",
        "felony",
    ),
    "health-care-costs": ("health care costs", "healthcare costs", "medical bill", "medical debt", "insurance premium", "prescription cost", "drug price", "copay", "deductible"),
    "food-costs-security": ("grocery", "food prices", "food costs", "food security", "snap benefits"),
    "federal-budget-debt": ("federal budget", "national debt", "deficit", "government spending", "debt ceiling"),
    "welfare-entitlements": ("welfare", "public benefits", "entitlement reform", "benefit eligibility"),
    "wages": ("minimum wage", "wage growth", "low pay", "pay raise", "worker pay", "wages"),
    "government-corruption": ("corruption", "government fraud", "ethics violation", "bribery", "accountability"),
    "social-security": ("social security", "retirement benefits", "social security benefits"),
    "trade-tariffs": ("tariff", "trade war", "trade agreement", "imports", "exports"),
}


@dataclass(frozen=True)
class Match:
    slug: str
    score: int
    matched_terms: tuple[str, ...]


def _metadata_target(provider: str, canonical_url: str) -> tuple[str, dict[str, str]]:
    if provider == "youtube":
        return "https://www.youtube.com/oembed", {"url": canonical_url, "format": "json"}
    if provider == "tiktok":
        return "https://www.tiktok.com/oembed", {"url": canonical_url}
    return canonical_url, {}


def fetch_social_metadata(provider: str, canonical_url: str) -> str:
    """Fetch only an already-validated provider URL or its fixed oEmbed endpoint."""
    target, params = _metadata_target(provider, canonical_url)
    response = requests.get(
        target,
        params=params or None,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/html;q=0.9"},
        timeout=METADATA_TIMEOUT,
        allow_redirects=False,
        stream=True,
    )
    response.raise_for_status()
    content_length = int(response.headers.get("content-length", "0") or 0)
    if content_length > MAX_METADATA_BYTES:
        raise ValueError("Social metadata response is too large")
    raw = b""
    for chunk in response.iter_content(32_768):
        raw += chunk
        if len(raw) > MAX_METADATA_BYTES:
            raise ValueError("Social metadata response is too large")
    content_type = response.headers.get("content-type", "").lower()
    if "json" in content_type:
        payload = json.loads(raw.decode(response.encoding or "utf-8"))
        return " ".join(str(payload.get(key, "")) for key in ("title", "author_name", "author_url"))
    soup = BeautifulSoup(raw, "html.parser")
    values = []
    if soup.title and soup.title.string:
        values.append(soup.title.string)
    for key in ("og:title", "og:description", "twitter:title", "twitter:description", "description"):
        node = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
        if node and node.get("content"):
            values.append(node["content"])
    return " ".join(values)


def rank_agenda_issues(text: str, available_slugs: Iterable[str]) -> list[Match]:
    normalized = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    matches: list[Match] = []
    for slug in available_slugs:
        found: list[str] = []
        score = 0
        for term in ISSUE_TERMS.get(slug, ()):
            clean = re.sub(r"[^a-z0-9]+", " ", term.lower()).strip()
            if re.search(rf"\b{re.escape(clean)}\b", normalized):
                found.append(term)
                score += 3 if " " in clean else 2
        if score:
            matches.append(Match(slug=slug, score=score, matched_terms=tuple(found)))
    return sorted(matches, key=lambda item: (-item.score, item.slug))


def confidence_for(matches: list[Match]) -> str:
    if not matches:
        return "low"
    lead = matches[0].score - (matches[1].score if len(matches) > 1 else 0)
    if matches[0].score >= 5 and lead >= 2:
        return "high"
    if matches[0].score >= 2:
        return "medium"
    return "low"
