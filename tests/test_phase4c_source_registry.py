import json
from pathlib import Path

from services.watch_phase4c_source_registry import (
    CONDITIONAL_REQUIREMENTS,
    DELIVERY_MODES,
    LOCAL_HOSTING_RIGHTS,
    REQUIRED_SOURCE_FIELDS,
    validate_source_registry,
)

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "config" / "watch_phase4c_source_registry.json"
REGISTRY = json.loads(PATH.read_text(encoding="utf-8"))


def _root(tmp_path, registry):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / PATH.name).write_text(json.dumps(registry), encoding="utf-8")
    return tmp_path


def _source(**changes):
    source = {
        "source_id": "example-agency",
        "publisher_name": "Example Agency",
        "source_state": "approved",
        "official_domains": ["example.gov"],
        "official_channels": ["https://video.example.gov/official"],
        "allowed_delivery_modes": ["official_embed"],
        "canonical_source_url": "https://example.gov/videos",
        "evidence": {
            "official_channel_reference": "https://video.example.gov/official",
            "embed_terms_url": "https://example.gov/video-policy",
            "embed_terms_reviewed_at": "2026-08-03T00:00:00Z",
            "privacy_reviewed_at": "2026-08-03T00:00:00Z"
        },
        "privacy": {"reviewed_at": "2026-08-03T00:00:00Z"},
        "poster": {"unknown_rights_fallback": "text_card"},
        "accessibility": {"captions_or_transcript_required": True},
        "review": {"reviewed_by": "policy-reviewer", "reviewed_at": "2026-08-03T00:00:00Z", "evidence_expires_at": "2027-08-03T00:00:00Z"},
        "takedown": {"contact": None}
    }
    source.update(changes)
    return source


def test_registry_approves_only_census_and_enables_nothing():
    report = validate_source_registry(root=ROOT)
    assert report.valid is True and report.error_codes == ()
    assert len(REGISTRY["sources"]) == 5 and REGISTRY["production_media_enabled"] is False
    census = next(source for source in REGISTRY["sources"] if source["source_id"] == "us-census-bureau")
    assert census["source_state"] == "approved"
    assert census["allowed_delivery_modes"] == ["official_embed", "link_out"]
    assert all(source["source_state"] == "candidate" for source in REGISTRY["sources"] if source is not census)
    assert all(source["allowed_delivery_modes"] == ["link_out"] for source in REGISTRY["sources"] if source is not census)
    assert REGISTRY["runtime_changes_authorized"] is False


def test_schema_matches_hybrid_delivery_contract():
    assert set(REGISTRY["delivery_modes"]) == DELIVERY_MODES
    assert set(REGISTRY["required_source_fields"]) == REQUIRED_SOURCE_FIELDS
    assert {mode: frozenset(fields) for mode, fields in REGISTRY["conditional_requirements"].items()} == CONDITIONAL_REQUIREMENTS
    assert set(REGISTRY["global_guards"]["local_hosting_rights_bases"]) == LOCAL_HOSTING_RIGHTS


def test_complete_official_embed_source_is_accepted(tmp_path):
    changed = json.loads(json.dumps(REGISTRY))
    changed["sources"] = [_source()]
    assert validate_source_registry(root=_root(tmp_path, changed)).valid is True


def test_unapproved_source_can_only_link_out(tmp_path):
    changed = json.loads(json.dumps(REGISTRY))
    changed["sources"] = [_source(source_state="candidate")]
    report = validate_source_registry(root=_root(tmp_path, changed))
    assert "unapproved_playback_mode" in report.error_codes


def test_census_approval_fails_closed_without_terms_privacy_or_accessibility(tmp_path):
    changed = json.loads(json.dumps(REGISTRY))
    census = next(source for source in changed["sources"] if source["source_id"] == "us-census-bureau")
    census["evidence"].pop("embed_terms_reviewed_at")
    census["privacy"]["reviewed_at"] = None
    census["accessibility"]["captions_or_transcript_required"] = False
    report = validate_source_registry(root=_root(tmp_path, changed))
    assert {"conditional_evidence_missing", "privacy_review_missing", "accessibility_requirement_missing"} <= set(report.error_codes)


def test_embed_missing_terms_privacy_or_accessibility_fails_closed(tmp_path):
    changed = json.loads(json.dumps(REGISTRY))
    changed["sources"] = [_source(evidence={}, privacy={}, accessibility={})]
    report = validate_source_registry(root=_root(tmp_path, changed))
    assert {"conditional_evidence_missing", "privacy_review_missing", "accessibility_requirement_missing"} <= set(report.error_codes)


def test_hosting_without_eligible_rights_basis_fails_closed(tmp_path):
    changed = json.loads(json.dumps(REGISTRY))
    source = _source(allowed_delivery_modes=["licensed_hosted"])
    source["evidence"] = {
        "rights_basis": "official_embed_terms",
        "license_or_agreement_reference": "https://example.gov/terms",
        "allowed_uses": ["embed"],
        "rights_reviewed_at": "2026-08-03T00:00:00Z"
    }
    changed["sources"] = [source]
    assert "hosting_rights_invalid" in validate_source_registry(root=_root(tmp_path, changed)).error_codes


def test_registry_slice_adds_no_runtime_or_media_surface():
    paths = {
        "config/watch_phase4c_source_registry.json",
        "docs/phase4c/SOURCE_REGISTRY.md",
        "services/watch_phase4c_source_registry.py",
        "tests/test_phase4c_source_registry.py",
    }
    assert all(not path.startswith(("data/", "models/", "routers/", "jobs/", "alembic/", "alembic_canonical/", "frontend/", "mobile/")) for path in paths)
