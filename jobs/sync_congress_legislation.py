"""Incrementally synchronize a Congress.gov bill collection.

The list endpoint is cheap enough to scan on every run. Bill detail resources are
only fetched when Congress.gov's ``updateDate`` changes (or a row still needs
enrichment), making restarts idempotent and keeping normal daily runs bounded.
No API key or raw response URL containing a key is ever persisted.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from models.database import Base, Bill, BillAction, MemberBillGroundTruth, PipelineRun
from utils.normalization import compute_action_dedupe_hash, extract_chamber_from_action, extract_committee_from_action

API_ROOT = "https://api.congress.gov/v3"
SOURCE_NAME = "congress.gov.api.v3"
VALID_TYPES = {"hr", "s", "hjres", "sjres", "hconres", "sconres", "hres", "sres"}


class RequestBudgetExhausted(RuntimeError):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_date(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def clean_html(value: str | None) -> str | None:
    if not value:
        return None
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(re.sub(r"\s+", " ", value)).strip()
    return value or None


def content_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def classify_status(actions: Iterable[dict[str, Any]]) -> tuple[str, str | None]:
    """Classify the furthest authoritative lifecycle milestone in an action set."""
    actions = list(actions)
    ranked: tuple[int, str, str | None] = (0, "introduced", None)
    for action in actions:
        text = str(action.get("text") or "").strip()
        lower = text.lower()
        code = str(action.get("actionCode") or "").lower()
        candidate = (0, "introduced")
        if "became public law" in lower or "became private law" in lower or "signed by president" in lower:
            candidate = (70, "enacted")
        elif "vetoed by president" in lower or "presidential veto" in lower:
            candidate = (65, "vetoed")
        elif "presented to president" in lower or "sent to the president" in lower:
            candidate = (60, "president")
        elif "cleared for white house" in lower or "passed congress" in lower:
            candidate = (55, "passed_both")
        elif "passed/agreed to in senate" in lower or re.search(r"\bpassed senate\b", lower):
            candidate = (45, "passed_senate")
        elif "passed/agreed to in house" in lower or re.search(r"\bpassed house\b", lower):
            candidate = (45, "passed_house")
        elif "ordered to be reported" in lower or "ordered the bill reported" in lower or "reported by the committee" in lower or "committee on" in lower and "reported" in lower:
            candidate = (35, "passed_committee")
        elif "referred to the committee" in lower or "referred to the subcommittee" in lower or "committee consideration" in lower:
            candidate = (25, "in_committee")
        elif "introduced" in lower or code.startswith("intro"):
            candidate = (10, "introduced")
        if candidate[0] >= ranked[0]:
            ranked = (candidate[0], candidate[1], text or None)

    # Both chambers passing is stronger than either individual result.
    passed_house = any("passed house" in str(a.get("text") or "").lower() or "passed/agreed to in house" in str(a.get("text") or "").lower() for a in actions)
    passed_senate = any("passed senate" in str(a.get("text") or "").lower() or "passed/agreed to in senate" in str(a.get("text") or "").lower() for a in actions)
    if passed_house and passed_senate and ranked[0] < 55:
        ranked = (55, "passed_both", "Passed both chambers")
    return ranked[1], ranked[2]


class CongressClient:
    def __init__(self, api_key: str, *, max_requests: int = 4500, delay: float = 0.05, session=None):
        if not api_key:
            raise ValueError("API_KEY_CONGRESS or CONGRESS_API_KEY is required")
        self.api_key = api_key
        self.max_requests = max_requests
        self.delay = delay
        self.requests_made = 0
        self.http = session or requests.Session()

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.requests_made >= self.max_requests:
            raise RequestBudgetExhausted(f"request budget {self.max_requests} exhausted")
        query = {"format": "json", "api_key": self.api_key, **(params or {})}
        url = f"{API_ROOT}{path}"
        last_error = ""
        for attempt in range(5):
            self.requests_made += 1
            response = self.http.get(url, params=query, timeout=45)
            if response.status_code == 200:
                if self.delay:
                    time.sleep(self.delay)
                payload = response.json()
                if not isinstance(payload, dict):
                    raise ValueError(f"non-object response from {path}")
                return payload
            last_error = f"HTTP {response.status_code}: {response.text[:300]}"
            if response.status_code not in {429, 500, 502, 503, 504}:
                break
            time.sleep(min(2 ** attempt, 20))
        raise RuntimeError(f"Congress.gov {path} failed: {last_error}")

    def paged(self, path: str, key: str, *, max_items: int | None = None, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        offset = 0
        while True:
            payload = self.get(path, {"limit": 250, "offset": offset, **(params or {})})
            page = payload.get(key) or []
            if not isinstance(page, list):
                raise ValueError(f"{path} returned invalid {key}")
            items.extend(item for item in page if isinstance(item, dict))
            if max_items is not None and len(items) >= max_items:
                return items[:max_items]
            count = int((payload.get("pagination") or {}).get("count") or len(items))
            if not page or len(items) >= count:
                return items
            offset += len(page)


def _meta(bill: Bill) -> dict[str, Any]:
    return bill.metadata_json if isinstance(bill.metadata_json, dict) else {}


def _needs_detail(existing: Bill | None, index_item: dict[str, Any], refresh_all: bool) -> bool:
    if refresh_all or existing is None or existing.needs_enrichment:
        return True
    prior = (_meta(existing).get("congress_sync") or {}).get("api_update_date")
    return prior != index_item.get("updateDate")


def _best_summary(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    rows = payload.get("summaries") or []
    if not rows:
        return None, None
    best = max(rows, key=lambda row: (str(row.get("actionDate") or ""), str(row.get("updateDate") or "")))
    return clean_html(best.get("text")), best.get("updateDate") or best.get("actionDate")


def _best_text_url(payload: dict[str, Any]) -> str | None:
    rows = payload.get("textVersions") or []
    if not rows:
        return None
    latest = max(rows, key=lambda row: str(row.get("date") or ""))
    formats = latest.get("formats") or []
    for preferred in ("Formatted Text", "PDF", "XML"):
        for item in formats:
            if item.get("type") == preferred and item.get("url"):
                return item["url"]
    return next((item.get("url") for item in formats if item.get("url")), None)


def _subjects(payload: dict[str, Any]) -> list[str]:
    block = payload.get("subjects") or {}
    rows = block.get("legislativeSubjects") or []
    return sorted({str(row.get("name")).strip() for row in rows if row.get("name")})


def sync_bill(db, client: CongressClient, index_item: dict[str, Any], *, refresh_all: bool = False) -> str:
    congress = int(index_item["congress"])
    bill_type = str(index_item["type"]).lower()
    number = int(index_item["number"])
    if bill_type not in VALID_TYPES:
        raise ValueError(f"unsupported bill type {bill_type}")
    bill_id = f"{bill_type}{number}-{congress}"
    existing = db.get(Bill, bill_id)
    if not _needs_detail(existing, index_item, refresh_all):
        return "unchanged"

    base = f"/bill/{congress}/{bill_type}/{number}"
    detail_payload = client.get(base)
    detail = detail_payload.get("bill")
    if not isinstance(detail, dict) or int(detail.get("congress") or 0) != congress:
        raise ValueError(f"invalid bill detail for {bill_id}")
    actions = client.paged(f"{base}/actions", "actions")
    cosponsors = client.paged(f"{base}/cosponsors", "cosponsors")
    summaries_payload = client.get(f"{base}/summaries")
    subjects_payload = client.get(f"{base}/subjects")
    text_payload = client.get(f"{base}/text")
    summary_text, summary_date = _best_summary(summaries_payload)
    status_bucket, status_reason = classify_status(actions)
    latest = detail.get("latestAction") or index_item.get("latestAction") or {}
    retrieved_at = utcnow()
    sources = {
        "detail": detail_payload,
        "actions": actions,
        "cosponsors": cosponsors,
        "summaries": summaries_payload.get("summaries") or [],
        "subjects": subjects_payload.get("subjects") or {},
        "text": text_payload.get("textVersions") or [],
    }
    provenance = {
        "source": SOURCE_NAME,
        "api_update_date": index_item.get("updateDate") or detail.get("updateDate"),
        "retrieved_at": retrieved_at.isoformat(),
        "content_sha256": content_hash(sources),
        "endpoint": f"{API_ROOT}{base}",
        "completeness": {
            "actions": True, "cosponsors": True, "summaries": True,
            "subjects": True, "text_versions": True,
        },
    }
    metadata = dict(detail)
    metadata["congress_sync"] = provenance
    bill = existing or Bill(bill_id=bill_id, congress=congress, bill_type=bill_type, bill_number=number)
    bill.title = detail.get("title") or index_item.get("title")
    bill.policy_area = (detail.get("policyArea") or {}).get("name")
    bill.status_bucket = status_bucket
    bill.status_reason = status_reason
    bill.latest_action_text = latest.get("text")
    bill.latest_action_date = parse_date(latest.get("actionDate"))
    bill.introduced_date = parse_date(detail.get("introducedDate"))
    bill.summary_text = summary_text
    bill.summary_date = summary_date
    bill.subjects_json = _subjects(subjects_payload)
    bill.full_text_url = _best_text_url(text_payload)
    bill.needs_enrichment = 0
    bill.metadata_json = metadata
    if existing is None:
        db.add(bill)
        db.flush()

    db.query(BillAction).filter(BillAction.bill_id == bill_id).delete(synchronize_session=False)
    seen_action_hashes: set[str] = set()
    for action in actions:
        action_text = str(action.get("text") or "").strip()
        action_date = parse_date(action.get("actionDate"))
        if not action_text or not action_date:
            continue
        code = action.get("actionCode")
        dedupe = compute_action_dedupe_hash(bill_id, str(action.get("actionDate")), action_text)
        if dedupe in seen_action_hashes:
            continue
        seen_action_hashes.add(dedupe)
        db.add(BillAction(
            bill_id=bill_id, action_date=action_date, action_text=action_text,
            action_code=code, chamber=extract_chamber_from_action(code, action_text),
            committee=extract_committee_from_action(action_text, action), raw_json=action,
            dedupe_hash=dedupe,
        ))

    db.query(MemberBillGroundTruth).filter(
        MemberBillGroundTruth.bill_id == bill_id,
        MemberBillGroundTruth.role.in_(["sponsored", "cosponsored", "sponsor", "cosponsor"]),
    ).delete(synchronize_session=False)
    seen_links: set[tuple[str, str]] = set()
    for sponsor in detail.get("sponsors") or []:
        if sponsor.get("bioguideId"):
            link = (sponsor["bioguideId"], "sponsored")
            if link not in seen_links:
                seen_links.add(link)
                db.add(MemberBillGroundTruth(bioguide_id=link[0], bill_id=bill_id, role=link[1], source=SOURCE_NAME, fetched_at=retrieved_at))
    for cosponsor in cosponsors:
        if cosponsor.get("bioguideId") and not cosponsor.get("sponsorshipWithdrawnDate"):
            link = (cosponsor["bioguideId"], "cosponsored")
            if link not in seen_links:
                seen_links.add(link)
                db.add(MemberBillGroundTruth(bioguide_id=link[0], bill_id=bill_id, role=link[1], source=SOURCE_NAME, fetched_at=retrieved_at))
    return "created" if existing is None else "updated"


def run(db_url: str, client: CongressClient, *, congress: int, refresh_all: bool = False, max_bills: int | None = None) -> dict[str, Any]:
    engine = create_engine(db_url)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    run_id = f"congress-legislation-{uuid.uuid4()}"
    started = utcnow()
    counts = {"indexed": 0, "created": 0, "updated": 0, "unchanged": 0, "failed": 0}
    failures: list[dict[str, str]] = []
    with Session() as db:
        manifest = PipelineRun(run_id=run_id, started_at=started, args_json=json.dumps({"congress": congress, "refresh_all": refresh_all, "max_bills": max_bills}), status="running")
        db.add(manifest)
        db.commit()
        try:
            index = client.paged(
                f"/bill/{congress}", "bills", max_items=max_bills,
                params={"sort": "updateDate+desc"},
            )
            counts["indexed"] = len(index)
            for item in index[:max_bills] if max_bills else index:
                try:
                    outcome = sync_bill(db, client, item, refresh_all=refresh_all)
                    counts[outcome] += 1
                    db.commit()
                except RequestBudgetExhausted:
                    db.rollback()
                    raise
                except Exception as exc:
                    db.rollback()
                    counts["failed"] += 1
                    failures.append({"bill": f"{item.get('type')}{item.get('number')}-{item.get('congress')}", "error": str(exc)})
            status = "success" if not failures else "partial"
        except RequestBudgetExhausted as exc:
            status = "checkpoint"
            failures.append({"bill": "checkpoint", "error": str(exc)})
        except Exception as exc:
            status = "failed"
            failures.append({"bill": "run", "error": str(exc)})
        manifest = db.get(PipelineRun, run_id)
        manifest.status = status
        manifest.finished_at = utcnow()
        manifest.counts_json = json.dumps({**counts, "requests": client.requests_made})
        manifest.error = json.dumps(failures[:100]) if failures else None
        db.commit()
    return {"run_id": run_id, "status": status, "congress": congress, **counts, "requests": client.requests_made, "failures": failures}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--congress", type=int, default=int(os.getenv("WTP_CURRENT_CONGRESS", "119")))
    parser.add_argument("--db-url", default=os.getenv("WTP_DB_URL"))
    parser.add_argument("--max-requests", type=int, default=4500)
    parser.add_argument("--max-bills", type=int)
    parser.add_argument("--refresh-all", action="store_true")
    args = parser.parse_args()
    environment = (os.getenv("WTP_ENV") or "").strip().lower()
    enabled = (os.getenv("WTP_ENABLE_CONGRESS_LEGISLATION_SYNC") or "").strip() == "1"
    if environment in {"staging", "production"} and not enabled:
        print("Congress legislation sync disabled; set WTP_ENABLE_CONGRESS_LEGISLATION_SYNC=1")
        return 0
    if not args.db_url:
        raise SystemExit("--db-url or WTP_DB_URL is required")
    key = os.getenv("API_KEY_CONGRESS") or os.getenv("CONGRESS_API_KEY") or ""
    report = run(args.db_url, CongressClient(key, max_requests=args.max_requests), congress=args.congress, refresh_all=args.refresh_all, max_bills=args.max_bills)
    report_dir = Path(os.getenv("WTP_SYNC_REPORT_DIR") or ROOT / "runtime_data" / "sync_reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"congress-legislation-{utcnow().strftime('%Y%m%dT%H%M%SZ')}.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({**report, "report": str(report_path)}))
    return 0 if report["status"] in {"success", "checkpoint"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
