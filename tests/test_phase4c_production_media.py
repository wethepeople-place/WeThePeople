import json
from datetime import datetime, timezone
from pathlib import Path

from services.watch_phase4c_production_media import production_metadata, validate_production_media

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "config" / "watch_phase4c_production_media_allowlist.json"
DOCKERFILE = (ROOT / "Dockerfile").read_text(encoding="utf-8")


def _root(tmp_path, *, allowlist=None, registry=None, fixture=None):
    (tmp_path / "config").mkdir()
    (tmp_path / "runtime_data").mkdir()
    values = {
        "config/watch_phase4c_production_media_allowlist.json": allowlist or json.loads(PATH.read_text(encoding="utf-8")),
        "config/watch_phase4c_source_registry.json": registry or json.loads((ROOT / "config/watch_phase4c_source_registry.json").read_text(encoding="utf-8")),
        "runtime_data/watch_census_production_pilot.json": fixture or json.loads((ROOT / "runtime_data/watch_census_production_pilot.json").read_text(encoding="utf-8")),
    }
    for relative, value in values.items():
        (tmp_path / relative).write_text(json.dumps(value), encoding="utf-8")
    return tmp_path


def test_exact_production_allowlist_is_valid_and_returns_three_bounded_items():
    now = datetime(2026, 8, 4, tzinfo=timezone.utc)
    assert validate_production_media(root=ROOT, now=now).valid is True
    delivery, accessibility = production_metadata("housing-rent-road-act-explained", root=ROOT, now=now)
    assert delivery["mode"] == "official_embed" and delivery["development_only"] is False
    assert accessibility["official_transcript_label"] == "Official enrolled H.R. 6644" and accessibility["development_only"] is False
    fallback, fallback_accessibility = production_metadata("housing-rent-road-act-explained", root=ROOT, now=now, embed_enabled=False)
    assert fallback["mode"] == "link_out" and fallback["canonical_url"].startswith("https://www.youtube.com/")
    assert fallback_accessibility["official_transcript_label"] == "Official enrolled H.R. 6644"
    tiktok, _ = production_metadata("housing-rent-road-act-becomes-law", root=ROOT, now=now)
    facebook, _ = production_metadata("housing-rent-road-act-speaker", root=ROOT, now=now)
    assert tiktok["provider"] == "tiktok" and facebook["provider"] == "facebook"
    assert production_metadata("not-allowlisted", root=ROOT, now=now) == (None, None)


def test_production_media_inputs_are_baked_outside_the_database_volume():
    assert "COPY config/ config/" in DOCKERFILE
    assert "COPY runtime_data/watch_census_production_pilot.json runtime_data/watch_census_production_pilot.json" in DOCKERFILE
    assert json.loads(PATH.read_text(encoding="utf-8"))["production_fixture"] == "runtime_data/watch_census_production_pilot.json"


def test_expired_evidence_fails_closed(tmp_path):
    report = validate_production_media(root=_root(tmp_path), now=datetime(2026, 11, 11, tzinfo=timezone.utc))
    assert "production_evidence_expired" in report.error_codes
    fallback, accessibility = production_metadata("housing-rent-road-act-explained", root=tmp_path, now=datetime(2026, 11, 11, tzinfo=timezone.utc))
    assert fallback["mode"] == "link_out" and accessibility["text_kind"] == "overview"


def test_source_or_item_identity_drift_fails_closed(tmp_path):
    allowlist = json.loads(PATH.read_text(encoding="utf-8"))
    allowlist["items"][0]["provider_video_id"] = "different"
    report = validate_production_media(root=_root(tmp_path, allowlist=allowlist), now=datetime(2026, 8, 4, tzinfo=timezone.utc))
    assert {"delivery_contract_invalid", "fixture_delivery_mismatch"} <= set(report.error_codes)


def test_mobile_credentials_downloads_and_ingestion_remain_forbidden(tmp_path):
    allowlist = json.loads(PATH.read_text(encoding="utf-8"))
    allowlist["mobile_inline_embed_allowed"] = True
    allowlist["credentials_allowed"] = True
    report = validate_production_media(root=_root(tmp_path, allowlist=allowlist), now=datetime(2026, 8, 4, tzinfo=timezone.utc))
    assert "operational_scope_drift" in report.error_codes
