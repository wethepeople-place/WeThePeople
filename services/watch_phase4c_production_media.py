"""Fail-closed exact-item production metadata gate for the Phase 4C pilot."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ProductionMediaValidation:
    valid: bool
    error_codes: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self) | {"error_codes": list(self.error_codes)}


def _read(root: Path, relative: str) -> dict:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _expires_in_future(value: object, now: datetime) -> bool:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed > now
    except ValueError:
        return False


def validate_production_media(*, root: Path = ROOT, now: datetime | None = None) -> ProductionMediaValidation:
    errors: set[str] = set()
    now = now or datetime.now(timezone.utc)
    try:
        allowlist = _read(root, "config/watch_phase4c_production_media_allowlist.json")
        registry = _read(root, "config/watch_phase4c_source_registry.json")
        fixture = _read(root, "data/watch_census_production_pilot.json")
    except (OSError, json.JSONDecodeError):
        return ProductionMediaValidation(False, ("production_media_inputs_unreadable",))

    if allowlist.get("production_media_enabled") is not True or allowlist.get("runtime_changes_authorized") is not True or allowlist.get("default_fallback") != "link_out":
        errors.add("production_authority_invalid")
    if allowlist.get("production_fixture") != "data/watch_census_production_pilot.json":
        errors.add("production_fixture_invalid")
    if any(allowlist.get(key) is not False for key in ("credentials_allowed", "downloads_allowed", "ingestion_allowed", "mobile_inline_embed_allowed")):
        errors.add("operational_scope_drift")
    items = allowlist.get("items")
    if not isinstance(items, list) or len(items) != 1:
        return ProductionMediaValidation(False, tuple(sorted(errors | {"allowlist_scope_invalid"})))
    item = items[0]
    if item.get("video_id") != "housing-rent-why-rents-move" or item.get("source_id") != "us-census-bureau" or item.get("delivery_mode") != "official_embed":
        errors.add("allowlist_identity_invalid")
    if item.get("provider") != "youtube" or item.get("provider_video_id") != "-Zfh6IKiJ4s" or item.get("mobile_delivery_mode") != "link_out":
        errors.add("delivery_contract_invalid")
    if item.get("web_consent_required") is not True or item.get("web_privacy_enhanced_host_required") is not True:
        errors.add("web_safeguard_missing")
    if not _expires_in_future(item.get("evidence_expires_at"), now):
        errors.add("production_evidence_expired")

    source = next((source for source in registry.get("sources", ()) if source.get("source_id") == item.get("source_id")), {})
    if source.get("source_state") != "approved" or "official_embed" not in source.get("allowed_delivery_modes", ()):
        errors.add("source_not_approved")
    if source.get("review", {}).get("evidence_expires_at") != item.get("evidence_expires_at"):
        errors.add("expiry_mismatch")
    record = next((record for record in fixture.get("videos", ()) if record.get("video_id") == item.get("video_id")), {})
    delivery = record.get("delivery", {})
    accessibility = record.get("accessibility", {})
    if any(delivery.get(key) != item.get(key) for key in ("provider", "provider_video_id", "canonical_url")):
        errors.add("fixture_delivery_mismatch")
    if accessibility.get("official_transcript_url") != item.get("official_transcript_url") or accessibility.get("text_kind") != "overview":
        errors.add("fixture_accessibility_mismatch")

    return ProductionMediaValidation(not errors, tuple(sorted(errors)))


def production_metadata(video_id: str, *, root: Path = ROOT, now: datetime | None = None, embed_enabled: bool = True) -> tuple[dict | None, dict | None]:
    try:
        allowlist = _read(root, "config/watch_phase4c_production_media_allowlist.json")
        item = next((item for item in allowlist.get("items", ()) if item.get("video_id") == video_id), None)
        fixture = _read(root, "data/watch_census_production_pilot.json")
        record = next((record for record in fixture.get("videos", ()) if record.get("video_id") == video_id), None)
    except (OSError, json.JSONDecodeError):
        return None, None
    if item is None or record is None:
        return None, None
    accessibility = dict(record["accessibility"]) | {"development_only": False}
    if not embed_enabled or not validate_production_media(root=root, now=now).valid:
        return {
            "mode": "link_out",
            "canonical_url": item.get("canonical_url"),
            "development_only": False,
        }, accessibility
    return dict(record["delivery"]) | {"development_only": False}, accessibility
