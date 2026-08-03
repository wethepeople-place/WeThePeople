"""Read-only, network-free validator for the Phase 4C approved-source registry."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DELIVERY_MODES = frozenset({"official_embed", "licensed_hosted", "publisher_feed_embed", "publisher_feed_hosted", "link_out"})
SOURCE_STATES = frozenset({"candidate", "approved", "suspended", "withdrawn"})
LOCAL_HOSTING_RIGHTS = frozenset({"owned", "licensed", "public_domain", "publisher_agreement"})
REQUIRED_SOURCE_FIELDS = frozenset({
    "source_id", "publisher_name", "source_state", "official_domains", "official_channels",
    "allowed_delivery_modes", "canonical_source_url", "evidence", "privacy", "poster",
    "accessibility", "review", "takedown",
})
CONDITIONAL_REQUIREMENTS = {
    "official_embed": frozenset({"official_channel_reference", "embed_terms_url", "embed_terms_reviewed_at", "privacy_reviewed_at"}),
    "licensed_hosted": frozenset({"rights_basis", "license_or_agreement_reference", "allowed_uses", "rights_reviewed_at"}),
    "publisher_feed_embed": frozenset({"publisher_warranty_reference", "feed_identity", "official_channel_reference", "embed_terms_url", "takedown_contact", "audit_retention"}),
    "publisher_feed_hosted": frozenset({"publisher_warranty_reference", "feed_identity", "rights_basis", "license_or_agreement_reference", "allowed_uses", "takedown_contact", "audit_retention"}),
    "link_out": frozenset({"canonical_source_url"}),
}


@dataclass(frozen=True)
class SourceRegistryValidation:
    valid: bool
    error_codes: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self) | {"error_codes": list(self.error_codes)}


def _https_url(value: object) -> bool:
    parsed = urlparse(value) if isinstance(value, str) else None
    return bool(parsed and parsed.scheme == "https" and parsed.hostname)


def _host_is_official(url: object, domains: list[str]) -> bool:
    if not _https_url(url):
        return False
    host = urlparse(url).hostname or ""
    return any(host == domain or host.endswith(f".{domain}") for domain in domains)


def validate_source_registry(*, root: Path = ROOT) -> SourceRegistryValidation:
    errors: set[str] = set()
    try:
        registry = json.loads((root / "config" / "watch_phase4c_source_registry.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return SourceRegistryValidation(False, ("registry_unreadable",))

    if registry.get("posture") != "contract_only_no_network_no_production_media" or registry.get("runtime_changes_authorized") is not False or registry.get("production_media_enabled") is not False:
        errors.add("operational_boundary_drift")
    if registry.get("default_fallback") != "link_out" or set(registry.get("source_states", ())) != SOURCE_STATES or set(registry.get("delivery_modes", ())) != DELIVERY_MODES:
        errors.add("registry_policy_drift")
    if set(registry.get("required_source_fields", ())) != REQUIRED_SOURCE_FIELDS:
        errors.add("registry_schema_drift")
    configured_conditions = {mode: frozenset(fields) for mode, fields in registry.get("conditional_requirements", {}).items()}
    if configured_conditions != CONDITIONAL_REQUIREMENTS:
        errors.add("conditional_schema_drift")
    guards = registry.get("global_guards", {})
    required_true = (
        "approved_required_for_non_link_out", "official_domains_https_only", "delivery_reference_must_match_official_domain_or_channel",
        "captions_or_transcript_required_for_playback", "poster_requires_owned_licensed_publisher_supplied_or_embed_rendered_basis",
        "text_card_fallback_allowed", "privacy_review_required_for_embed", "unknown_or_expired_evidence_falls_back_to_link_out",
    )
    required_false = ("network_fetch_allowed", "credentials_allowed", "download_allowed", "external_publish_allowed")
    if any(guards.get(key) is not True for key in required_true) or any(guards.get(key) is not False for key in required_false) or set(guards.get("local_hosting_rights_bases", ())) != LOCAL_HOSTING_RIGHTS:
        errors.add("global_guard_drift")

    sources = registry.get("sources", ())
    if not isinstance(sources, list):
        return SourceRegistryValidation(False, tuple(sorted(errors | {"sources_not_list"})))
    ids: set[str] = set()
    for source in sources:
        if not isinstance(source, dict) or not REQUIRED_SOURCE_FIELDS <= set(source):
            errors.add("source_fields_missing")
            continue
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", source_id) or source_id in ids:
            errors.add("source_identity_invalid")
        else:
            ids.add(source_id)
        state = source.get("source_state")
        modes = set(source.get("allowed_delivery_modes", ()))
        if state not in SOURCE_STATES or not modes or not modes <= DELIVERY_MODES:
            errors.add("source_policy_invalid")
            continue
        domains = source.get("official_domains")
        channels = source.get("official_channels")
        canonical = source.get("canonical_source_url")
        if not isinstance(domains, list) or not domains or any(not _https_url(f"https://{domain}") or "/" in domain for domain in domains):
            errors.add("official_domain_invalid")
        if not isinstance(channels, list) or any(not _host_is_official(channel, domains) for channel in channels):
            errors.add("official_channel_invalid")
        if not _host_is_official(canonical, domains):
            errors.add("canonical_source_invalid")
        if state != "approved" and modes != {"link_out"}:
            errors.add("unapproved_playback_mode")
        evidence = source.get("evidence") if isinstance(source.get("evidence"), dict) else {}
        for mode in modes:
            if not CONDITIONAL_REQUIREMENTS[mode] <= set(evidence) | {"canonical_source_url"}:
                errors.add("conditional_evidence_missing")
        if modes & {"official_embed", "publisher_feed_embed"} and evidence.get("official_channel_reference") not in channels:
            errors.add("embed_channel_unverified")
        if modes & {"licensed_hosted", "publisher_feed_hosted"} and evidence.get("rights_basis") not in LOCAL_HOSTING_RIGHTS:
            errors.add("hosting_rights_invalid")
        accessibility = source.get("accessibility") if isinstance(source.get("accessibility"), dict) else {}
        if modes != {"link_out"} and accessibility.get("captions_or_transcript_required") is not True:
            errors.add("accessibility_requirement_missing")
        poster = source.get("poster") if isinstance(source.get("poster"), dict) else {}
        if poster.get("unknown_rights_fallback") != "text_card":
            errors.add("poster_fallback_invalid")
        privacy = source.get("privacy") if isinstance(source.get("privacy"), dict) else {}
        if modes & {"official_embed", "publisher_feed_embed"} and privacy.get("reviewed_at") is None:
            errors.add("privacy_review_missing")
        review = source.get("review") if isinstance(source.get("review"), dict) else {}
        if state == "approved" and not all(review.get(key) for key in ("reviewed_by", "reviewed_at", "evidence_expires_at")):
            errors.add("approval_review_missing")
        takedown = source.get("takedown") if isinstance(source.get("takedown"), dict) else {}
        if modes & {"publisher_feed_embed", "publisher_feed_hosted"} and not takedown.get("contact"):
            errors.add("takedown_contact_missing")

    return SourceRegistryValidation(not errors, tuple(sorted(errors)))
