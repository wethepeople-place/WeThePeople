from datetime import datetime, timedelta, timezone

import pytest

from services.media_safety_contracts import (
    DeletionState,
    FakeQuarantineStore,
    MediaMetadata,
    MediaSafetyConflictError,
    MediaSafetyGate,
    MediaSafetyValidationError,
    QuarantineConstraints,
    QuarantineObservation,
    QuarantineStore,
    ScannerResult,
    ScannerVerdict,
)


NOW = datetime(2026, 8, 5, 16, 0, tzinfo=timezone.utc)
SHA = "a" * 64


def constraints(**overrides):
    values = {
        "creator_id": "creator-1",
        "asset_id": "asset-1",
        "asset_version": 1,
        "expected_bytes": 1_000_000,
        "expected_sha256": SHA,
        "mime_type": "video/mp4",
        "cors_origin": "https://app.wethepeople.place",
        "expires_in_seconds": 900,
        "active_uploads": 0,
        "max_active_uploads": 2,
        "spend_guard_healthy": True,
        "idempotency_key": "upload:asset-1:v1",
    }
    values.update(overrides)
    return QuarantineConstraints(**values)


def observation(authorization, **overrides):
    values = {
        "asset_id": authorization.asset_id,
        "asset_version": authorization.asset_version,
        "object_key": authorization.object_key,
        "byte_size": 1_000_000,
        "sha256": SHA,
        "etag": "multipart-etag-3",
        "observed_at": NOW,
    }
    values.update(overrides)
    return QuarantineObservation(**values)


def scanner(**overrides):
    values = {
        "asset_id": "asset-1",
        "asset_version": 1,
        "sha256": SHA,
        "verdict": ScannerVerdict.CLEAN,
        "engine_version": "synthetic-engine-1",
        "signature_version": "synthetic-signatures-1",
        "signatures_updated_at": NOW - timedelta(hours=1),
        "scanned_bytes": 1_000_000,
        "scan_seconds": 12,
    }
    values.update(overrides)
    return ScannerResult(**values)


def metadata(**overrides):
    values = {
        "asset_id": "asset-1",
        "asset_version": 1,
        "sha256": SHA,
        "container": "mp4",
        "video_codec": "h264",
        "audio_codec": "aac",
        "duration_seconds": 30.0,
        "width": 1080,
        "height": 1920,
        "frame_rate": 30.0,
        "tracks": ("video", "audio"),
    }
    values.update(overrides)
    return MediaMetadata(**values)


@pytest.fixture
def store():
    return FakeQuarantineStore(now=NOW)


def completed_source(store):
    authorization = store.create_upload_authorization(constraints())
    observed = store.record_completion(authorization, observation(authorization))
    return authorization, observed


def test_fake_satisfies_quarantine_protocol(store):
    adapter: QuarantineStore = store
    operations = {
        "create_upload_authorization",
        "record_completion",
        "evaluate_media_safety",
        "create_ingest_grant",
        "request_deletion",
        "verify_deletion",
    }
    assert all(callable(getattr(adapter, operation)) for operation in operations)


def test_upload_authorization_is_bound_private_and_idempotent(store):
    first = store.create_upload_authorization(constraints())
    second = store.create_upload_authorization(constraints())

    assert first == second
    assert first.creator_id == "creator-1"
    assert first.asset_version == 1
    assert first.expires_at == NOW + timedelta(minutes=15)
    assert first.object_key.startswith("development/quarantine/")
    assert first.upload_url.startswith("https://upload.invalid/")
    assert "creator-1" not in first.object_key
    assert "asset-1" not in first.upload_url


@pytest.mark.parametrize(
    "override,exception,code",
    [
        ({"creator_id": ""}, MediaSafetyValidationError, "invalid_creator_id"),
        ({"asset_version": 0}, MediaSafetyValidationError, "invalid_asset_version"),
        ({"expected_bytes": 2_000_000_001}, MediaSafetyValidationError, "invalid_source_size"),
        ({"expected_sha256": "bad"}, MediaSafetyValidationError, "invalid_sha256"),
        ({"mime_type": "application/octet-stream"}, MediaSafetyValidationError, "invalid_mime_type"),
        ({"cors_origin": "*"}, MediaSafetyValidationError, "invalid_cors_origin"),
        ({"cors_origin": "http://app.wethepeople.place"}, MediaSafetyValidationError, "invalid_cors_origin"),
        ({"expires_in_seconds": 901}, MediaSafetyValidationError, "invalid_upload_expiry"),
        ({"active_uploads": 2}, MediaSafetyConflictError, "upload_concurrency_exceeded"),
        ({"spend_guard_healthy": False}, MediaSafetyConflictError, "spend_guard_unhealthy"),
    ],
)
def test_upload_constraints_fail_closed(store, override, exception, code):
    with pytest.raises(exception, match=code):
        store.create_upload_authorization(constraints(**override))


def test_upload_idempotency_conflict_fails_closed(store):
    store.create_upload_authorization(constraints())
    with pytest.raises(MediaSafetyConflictError, match="idempotency_conflict"):
        store.create_upload_authorization(constraints(asset_version=2))


@pytest.mark.parametrize(
    "override,code",
    [
        ({"asset_id": "asset-2"}, "upload_binding_mismatch"),
        ({"asset_version": 2}, "upload_binding_mismatch"),
        ({"object_key": "development/quarantine/wrong"}, "upload_binding_mismatch"),
        ({"byte_size": 999_999}, "observed_size_mismatch"),
        ({"sha256": "b" * 64}, "checksum_mismatch"),
    ],
)
def test_completion_requires_exact_version_size_and_checksum(store, override, code):
    authorization = store.create_upload_authorization(constraints())
    with pytest.raises(MediaSafetyConflictError, match=code):
        store.record_completion(authorization, observation(authorization, **override))


def test_multipart_etag_is_not_used_as_checksum(store):
    authorization = store.create_upload_authorization(constraints())
    observed = store.record_completion(
        authorization,
        observation(authorization, etag="not-a-sha256-and-not-trusted"),
    )
    assert observed.sha256 == SHA
    assert observed.etag != observed.sha256


def test_clean_exact_source_passes_and_gets_short_lived_ingest_grant(store):
    authorization, observed = completed_source(store)
    decision = store.evaluate_media_safety(observed, scanner(), metadata(), NOW)
    grant = store.create_ingest_grant(decision, 300)

    assert decision.passed is True
    assert decision.reason_code == "passed"
    assert grant.object_key == authorization.object_key
    assert grant.sha256 == SHA
    assert grant.read_url.startswith("https://read.invalid/")
    assert grant.expires_at == NOW + timedelta(minutes=5)


def test_ingest_is_impossible_before_a_matching_pass(store):
    _, observed = completed_source(store)
    failed = store.evaluate_media_safety(
        observed, scanner(verdict=ScannerVerdict.TIMEOUT), metadata(), NOW
    )
    with pytest.raises(MediaSafetyConflictError, match="media_safety_not_passed"):
        store.create_ingest_grant(failed, 300)

    forged = failed.__class__("asset-1", 1, SHA, True, "passed", NOW)
    with pytest.raises(MediaSafetyConflictError, match="media_safety_decision_not_recorded"):
        store.create_ingest_grant(forged, 300)


@pytest.mark.parametrize(
    "scan_override,reason",
    [
        ({"verdict": ScannerVerdict.INFECTED}, "scanner_infected"),
        ({"verdict": ScannerVerdict.ERROR}, "scanner_error"),
        ({"verdict": ScannerVerdict.TIMEOUT}, "scanner_timeout"),
        ({"verdict": ScannerVerdict.UNSUPPORTED}, "scanner_unsupported"),
        ({"verdict": ScannerVerdict.STALE_SIGNATURES}, "scanner_stale_signatures"),
        ({"verdict": ScannerVerdict.SKIPPED_LIMIT}, "scanner_skipped_limit"),
        ({"signatures_updated_at": NOW - timedelta(hours=25)}, "stale_signatures"),
        ({"scanned_bytes": 999_999}, "scan_size_mismatch"),
        ({"scan_seconds": 1_801}, "scan_timeout"),
        ({"sha256": "b" * 64}, "scanner_binding_mismatch"),
    ],
)
def test_scanner_failures_normalize_without_security_details(store, scan_override, reason):
    _, observed = completed_source(store)
    decision = MediaSafetyGate().decide(observed, scanner(**scan_override), metadata(), now=NOW)
    assert decision.passed is False
    assert decision.reason_code == reason
    assert "synthetic-engine" not in decision.reason_code
    assert "synthetic-signatures" not in decision.reason_code


@pytest.mark.parametrize(
    "metadata_override,reason",
    [
        ({"sha256": "b" * 64}, "metadata_binding_mismatch"),
        ({"encrypted": True}, "encrypted_media"),
        ({"active_content": True}, "active_content"),
        ({"container": "mkv"}, "unsupported_container"),
        ({"video_codec": "vp9"}, "unsupported_video_codec"),
        ({"audio_codec": "mp3"}, "unsupported_audio_codec"),
        ({"duration_seconds": 181.0}, "invalid_duration"),
        ({"width": 1921}, "invalid_dimensions"),
        ({"height": 1921}, "invalid_dimensions"),
        ({"frame_rate": 30.1}, "invalid_frame_rate"),
        ({"tracks": ("audio", "video")}, "invalid_tracks"),
        ({"tracks": ("video", "audio", "attachment")}, "unexpected_tracks"),
        ({"tracks": ("video", "data")}, "unexpected_tracks"),
    ],
)
def test_media_parser_contract_rejects_unsupported_structure(store, metadata_override, reason):
    _, observed = completed_source(store)
    decision = MediaSafetyGate().decide(
        observed, scanner(), metadata(**metadata_override), now=NOW
    )
    assert decision.passed is False
    assert decision.reason_code == reason


def test_completion_and_deletion_are_idempotent_and_separately_verified(store):
    authorization, observed = completed_source(store)
    assert store.record_completion(authorization, observed) == observed

    first = store.request_deletion(authorization.object_key, "delete:asset-1:v1")
    second = store.request_deletion(authorization.object_key, "delete:asset-1:v1")
    assert first == second
    assert store.verify_deletion(authorization.object_key).state == DeletionState.PENDING

    store.mark_deleted(authorization.object_key)
    verified = store.verify_deletion(authorization.object_key)
    assert verified.state == DeletionState.VERIFIED
    assert verified.verified_at == NOW


def test_contract_is_network_and_environment_free(monkeypatch, store):
    monkeypatch.setattr(
        "socket.create_connection",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network attempted")),
    )
    monkeypatch.delenv("MUX_TOKEN_ID", raising=False)
    monkeypatch.delenv("R2_SECRET_ACCESS_KEY", raising=False)

    _, observed = completed_source(store)
    decision = store.evaluate_media_safety(observed, scanner(), metadata(), NOW)
    assert decision.passed is True
