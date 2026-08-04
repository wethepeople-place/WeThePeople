import json
from pathlib import Path

from services.watch_phase4c_census_item_review import validate_census_item_review


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "config" / "watch_phase4c_census_item_review.json"
REVIEW = json.loads(PATH.read_text(encoding="utf-8"))


def test_census_item_review_is_valid_and_fail_closed():
    report = validate_census_item_review(root=ROOT)
    assert report.valid is True and report.error_codes == ()
    assert REVIEW["recommendation"] == "eligible_for_separate_registry_approval_review"
    assert REVIEW["required_fallback"] == "link_out"


def test_exact_item_identity_and_first_party_evidence_are_recorded():
    record = REVIEW["record"]
    evidence = REVIEW["evidence"]
    assert record["video_id"] == "housing-rent-why-rents-move"
    assert record["provider_video_id"] == "-Zfh6IKiJ4s"
    assert evidence["census_page_embeds_exact_provider_video"] is True
    assert evidence["youtube_verified_publisher"] == "U.S. Census Bureau"
    assert evidence["official_transcript_present"] is True


def test_accessibility_and_privacy_pass_but_registry_remains_fail_closed():
    gates = REVIEW["gate_results"]
    assert gates["per_item_captions_or_full_transcript"] == "pass_via_official_transcript_link"
    assert gates["privacy_policy_link_in_consent_notice"] == "pass"
    assert gates["production_source_registry_state"] == "fail"
    assert REVIEW["blockers"] == ["source_registry_remains_candidate_link_out_only"]
    assert REVIEW["production_playback_authorized"] is False


def test_weakened_review_cannot_claim_approval(tmp_path):
    changed = json.loads(json.dumps(REVIEW))
    changed["recommendation"] = "approved"
    changed["required_fallback"] = "official_embed"
    changed["production_playback_authorized"] = True
    (tmp_path / "config").mkdir()
    (tmp_path / "data").mkdir()
    (tmp_path / "frontend" / "src" / "pages").mkdir(parents=True)
    for relative in ("config/watch_phase4c_source_registry.json", "data/watch_housing_rent.json"):
        source = ROOT / relative
        target = tmp_path / relative
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "config" / PATH.name).write_text(json.dumps(changed), encoding="utf-8")
    (tmp_path / "frontend" / "src" / "pages" / "WatchVideoPage.tsx").write_text("consent notice without direct policy link", encoding="utf-8")
    report = validate_census_item_review(root=tmp_path)
    assert {"recommendation_not_fail_closed", "operational_boundary_drift"} <= set(report.error_codes)
