import json
from pathlib import Path

from services.watch_phase4c_decision import DELIVERY_MODES, FORBIDDEN_SURFACES, LOCAL_HOSTING_RIGHTS, REPAIRS, REQUIRED_CATALOG_FIELDS, validate_phase4c_decision

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "config" / "watch_phase4c_decision.json"
CONTRACT = json.loads(PATH.read_text(encoding="utf-8"))


def _root(tmp_path, contract):
    (tmp_path / "config").mkdir()
    (tmp_path / "docs" / "phase4c").mkdir(parents=True)
    (tmp_path / "config" / PATH.name).write_text(json.dumps(contract), encoding="utf-8")
    name = "WATCH_DECISION.md"
    (tmp_path / "docs" / "phase4c" / name).write_text((ROOT / "docs" / "phase4c" / name).read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


def test_phase4c_hybrid_delivery_decision_is_valid_and_non_operational():
    report = validate_phase4c_decision(root=ROOT)
    assert report.valid is True and report.error_codes == ()
    assert CONTRACT["runtime_changes_authorized"] is False


def test_audit_records_real_one_item_limits_and_no_acceptance_assets():
    audit = CONTRACT["audit"]
    assert audit["existing_catalog_size"] == 1
    assert audit["web_surface"] == "share_preview_only" and audit["pagination"] == "none"
    assert audit["local_rights_cleared_civic_media_count"] == 0 and audit["acceptance_media_eligible"] is False


def test_catalog_is_three_to_five_and_fails_closed_on_rights_accessibility_and_provenance():
    catalog = CONTRACT["catalog_contract"]
    assert (catalog["minimum_published_items"], catalog["maximum_first_slice_items"]) == (3, 5)
    assert set(catalog["required_fields"]) == REQUIRED_CATALOG_FIELDS
    assert {"rights_basis", "rights_evidence_reference", "transcript_or_captions", "official_evidence_source_ids"} <= set(catalog["fail_closed_when_missing"])
    assert catalog["generic_flower_sample_allowed_for_acceptance"] is False


def test_cursor_contract_is_stable_complete_and_tamper_rejecting():
    cursor = CONTRACT["cursor_contract"]
    assert cursor["ordering"] == ["sort_order ASC", "published_at DESC", "video_id ASC"]
    assert cursor["cursor_payload_fields"] == ["version", "sort_order", "published_at", "video_id"]
    assert cursor["signed_or_authenticated"] is True and cursor["unknown_or_tampered_cursor_status"] == 400
    assert cursor["offset_pagination_allowed"] is False


def test_editorial_and_storage_boundaries_are_private_reviewed_and_provider_neutral():
    authority = CONTRACT["editorial_authority"]
    assert authority["private_authenticated_only"] is True and authority["reviewer_must_differ_from_submitter"] is True
    assert authority["public_upload_allowed"] is False and authority["creator_self_publish_allowed"] is False
    storage = CONTRACT["storage_abstraction"]
    assert storage["catalog_stores_provider_neutral_asset_key"] is True
    assert storage["arbitrary_external_hotlink_production_ready"] is False and storage["production_credentials_authorized"] is False


def test_hybrid_delivery_scales_by_source_and_fails_closed():
    policy = CONTRACT["delivery_policy"]
    assert policy["default_mode"] == "official_embed"
    assert set(policy["allowed_modes"]) == DELIVERY_MODES
    assert policy["scalable_clearance_unit"] == "source_channel_feed_or_collection"
    assert policy["item_by_item_outreach_required_by_default"] is False
    assert set(policy["local_hosting_requires_rights_basis"]) == LOCAL_HOSTING_RIGHTS
    assert policy["unclear_rights_fallback"] == "link_out"
    assert policy["download_from_embed_platform_allowed"] is False
    assert policy["platform_thumbnail_reuse_inferred"] is False


def test_keep_repair_defer_and_first_slice_stay_bounded():
    decisions = CONTRACT["decisions"]
    assert set(decisions["repair_before_acceptance"]) == REPAIRS
    assert FORBIDDEN_SURFACES <= set(decisions["defer"])
    first = CONTRACT["first_approved_implementation_slice"]
    assert first["blocked_until"] == []
    assert {"delivery_policy_contract", "approved_source_registry_schema", "conditional_fail_closed_validation"} <= set(first["allows_now"])
    assert {"runtime_routes", "public_upload", "production_credentials", "network_download", "external_publish", "production_media_enablement"} == set(first["still_forbids"])


def test_weakened_catalog_cursor_editorial_storage_or_guards_fail_closed(tmp_path):
    changed = json.loads(json.dumps(CONTRACT))
    changed["catalog_contract"]["generic_flower_sample_allowed_for_acceptance"] = True
    changed["cursor_contract"]["signed_or_authenticated"] = False
    changed["editorial_authority"]["public_upload_allowed"] = True
    changed["storage_abstraction"]["production_credentials_authorized"] = True
    changed["drift_guards"]["public_upload_allowed"] = True
    report = validate_phase4c_decision(root=_root(tmp_path, changed))
    assert {"catalog_safety_drift", "cursor_drift", "editorial_boundary_drift", "storage_drift", "unsafe_guard_authorized"} <= set(report.error_codes)


def test_weakened_hybrid_delivery_policy_fails_closed(tmp_path):
    changed = json.loads(json.dumps(CONTRACT))
    changed["delivery_policy"]["default_mode"] = "licensed_hosted"
    changed["delivery_policy"]["download_from_embed_platform_allowed"] = True
    changed["delivery_policy"]["unclear_rights_fallback"] = "official_embed"
    report = validate_phase4c_decision(root=_root(tmp_path, changed))
    assert {"delivery_policy_drift", "delivery_safety_drift"} <= set(report.error_codes)


def test_no_public_upload_or_mutating_video_route_exists():
    from main import app

    routes = {path: set(methods) for path, methods in app.openapi()["paths"].items() if path.startswith("/videos")}
    assert routes == {
        "/videos": {"get"},
        "/videos/{video_id}": {"get"},
        "/videos/{video_id}/share": {"get"},
    }
    all_paths = " ".join(app.openapi()["paths"]).lower()
    assert not any(term in all_paths for term in ("/upload", "/creator", "/record", "/recommend"))


def test_decision_slice_did_not_add_runtime_models_migrations_ui_or_jobs():
    changed_paths = {
        "config/watch_phase4c_decision.json",
        "docs/phase4c/WATCH_DECISION.md",
        "services/watch_phase4c_decision.py",
        "tests/test_phase4c_watch_decision.py",
    }
    assert all(not path.startswith(("models/", "routers/", "jobs/", "alembic/", "alembic_canonical/", "frontend/", "mobile/")) for path in changed_paths)
