import json
from datetime import datetime, timedelta, timezone

import pytest

from services.managed_video_provider import (
    FakeManagedVideoProvider,
    ManagedVideoProvider,
    ProcessingState,
    ProviderAuthorizationError,
    ProviderConflictError,
    ProviderSecurityError,
    ProviderValidationError,
    UploadConstraints,
    sign_fake_webhook,
)


NOW = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
SECRET = b"synthetic-contract-secret"


def constraints(**overrides):
    values = {
        "max_bytes": 2_000_000_000,
        "max_duration_seconds": 180,
        "allowed_mime_types": ("video/mp4", "video/quicktime"),
        "cors_origin": "https://app.wethepeople.place",
        "expires_in_seconds": 900,
        "quality": "basic",
        "idempotency_key": "upload:asset-1:v1",
    }
    values.update(overrides)
    return UploadConstraints(**values)


@pytest.fixture
def provider():
    fake = FakeManagedVideoProvider(now=NOW, webhook_secret=SECRET)
    fake.seed_asset("provider-asset-1")
    return fake


def test_fake_satisfies_ten_operation_protocol(provider):
    adapter: ManagedVideoProvider = provider
    operations = {
        "create_upload_authorization",
        "get_processing_state",
        "resolve_review_playback",
        "resolve_public_playback",
        "attach_captions",
        "get_asset_metadata",
        "request_master_export",
        "request_deletion",
        "verify_deletion",
        "verify_webhook",
    }
    assert all(callable(getattr(adapter, operation)) for operation in operations)


def test_upload_authorization_is_bounded_and_idempotent(provider):
    first = provider.create_upload_authorization("asset-1", constraints())
    second = provider.create_upload_authorization("asset-1", constraints())

    assert first == second
    assert first.expires_at == NOW + timedelta(minutes=15)
    assert first.upload_url.startswith("https://upload.invalid/")
    assert "asset-1" not in first.upload_url


@pytest.mark.parametrize(
    "override,code",
    [
        ({"max_bytes": 2_000_000_001}, "invalid_max_bytes"),
        ({"max_duration_seconds": 181}, "invalid_max_duration"),
        ({"cors_origin": "*"}, "invalid_cors_origin"),
        ({"cors_origin": "http://app.wethepeople.place"}, "invalid_cors_origin"),
        ({"expires_in_seconds": 901}, "invalid_upload_expiry"),
        ({"quality": "premium"}, "invalid_video_quality"),
    ],
)
def test_upload_constraints_fail_closed(provider, override, code):
    with pytest.raises(ProviderValidationError, match=code):
        provider.create_upload_authorization("asset-1", constraints(**override))


def test_idempotency_key_cannot_be_reused_for_different_input(provider):
    provider.create_upload_authorization("asset-1", constraints())
    with pytest.raises(ProviderConflictError, match="idempotency_conflict"):
        provider.create_upload_authorization("asset-2", constraints())


def test_processing_metadata_and_private_review_playback(provider):
    assert provider.get_processing_state("provider-asset-1").state == ProcessingState.READY
    assert provider.get_asset_metadata("provider-asset-1").duration_seconds == 30.0
    grant = provider.resolve_review_playback("provider-asset-1", 300)
    assert grant.expires_at == NOW + timedelta(minutes=5)
    assert grant.url.startswith("https://review.invalid/")


def test_readiness_does_not_enable_public_playback(provider):
    with pytest.raises(ProviderAuthorizationError, match="public_playback_not_enabled"):
        provider.resolve_public_playback("provider-asset-1")

    provider.seed_asset("provider-public-1", public=True)
    assert provider.resolve_public_playback("provider-public-1").expires_at is None


def test_captions_are_webvtt_only_and_idempotent(provider):
    first = provider.attach_captions(
        "provider-asset-1", "en-US", "WEBVTT\n\n00:00.000 --> 00:01.000\nHello\n", "captions:a1:en:v1"
    )
    second = provider.attach_captions(
        "provider-asset-1", "en-US", "WEBVTT\n\n00:00.000 --> 00:01.000\nHello\n", "captions:a1:en:v1"
    )
    assert first == second
    assert first.kind == "captions"

    with pytest.raises(ProviderValidationError, match="invalid_webvtt"):
        provider.attach_captions("provider-asset-1", "en", "1\n00:00 --> 00:01\nHello", "captions:bad")


def test_master_export_is_provider_neutral_and_idempotent(provider):
    first = provider.request_master_export("provider-asset-1", "master:a1:v1")
    second = provider.request_master_export("provider-asset-1", "master:a1:v1")
    assert first == second
    assert first.state == "preparing"
    assert first.url is None


def test_deletion_request_and_verification_are_separate(provider):
    first = provider.request_deletion("provider-asset-1", "delete:a1:v1")
    second = provider.request_deletion("provider-asset-1", "delete:a1:v1")
    assert first == second
    assert provider.verify_deletion("provider-asset-1").state == "pending"

    provider.mark_deleted("provider-asset-1")
    verified = provider.verify_deletion("provider-asset-1")
    assert verified.state == "verified"
    assert verified.verified_at == NOW


def webhook(provider, payload, observed_at=NOW, timestamp=None):
    raw = json.dumps(payload, separators=(",", ":")).encode()
    signed_at = int((timestamp or observed_at).timestamp())
    headers = {"Mux-Signature": sign_fake_webhook(SECRET, signed_at, raw)}
    return provider.verify_webhook(headers, raw, observed_at)


def test_webhook_is_verified_and_mapped_without_publication_state(provider):
    event = webhook(
        provider,
        {
            "id": "event-1",
            "type": "video.asset.ready",
            "data": {"id": "opaque-provider-asset", "status": "ready"},
        },
    )
    assert event.kind == "asset_ready"
    assert event.provider_asset_key == "opaque-provider-asset"
    assert event.provider_state == "ready"
    assert not hasattr(event, "publication_state")


def test_webhook_replay_invalid_signature_and_stale_timestamp_fail_closed(provider):
    payload = {"id": "event-2", "type": "video.asset.deleted", "data": {"id": "asset-x"}}
    webhook(provider, payload)
    with pytest.raises(ProviderSecurityError, match="replayed_webhook"):
        webhook(provider, payload)

    raw = json.dumps({"id": "event-3", "type": "video.asset.ready"}).encode()
    with pytest.raises(ProviderSecurityError, match="invalid_webhook_signature"):
        provider.verify_webhook({"Mux-Signature": "t=1785931200,v1=bad"}, raw, NOW)

    with pytest.raises(ProviderSecurityError, match="stale_webhook"):
        webhook(
            provider,
            {"id": "event-4", "type": "video.asset.ready"},
            timestamp=NOW - timedelta(minutes=6),
        )


def test_unknown_authenticated_webhook_is_ignored(provider):
    event = webhook(provider, {"id": "event-5", "type": "video.live_stream.active", "data": {}})
    assert event.kind == "ignored"


def test_error_messages_do_not_contain_capability_urls_or_secrets(provider):
    with pytest.raises(ProviderValidationError) as caught:
        provider.create_upload_authorization("asset-1", constraints(cors_origin="*"))
    rendered = str(caught.value)
    assert "contract-test-secret" not in rendered
    assert "https://" not in rendered
