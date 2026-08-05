"""Provider-neutral managed-video boundary and a network-free contract fake.

The fake exists to validate the Phase 4D adapter contract. It is not a Mux
client and must not be wired into runtime routes.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Mapping, Protocol


class ProcessingState(str, Enum):
    WAITING = "waiting"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    DELETED = "deleted"


class ProviderError(Exception):
    """Base error with a stable, non-sensitive code."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class ProviderValidationError(ProviderError):
    pass


class ProviderAuthenticationError(ProviderError):
    pass


class ProviderAuthorizationError(ProviderError):
    pass


class ProviderNotFoundError(ProviderError):
    pass


class ProviderConflictError(ProviderError):
    pass


class ProviderRateLimitedError(ProviderError):
    pass


class ProviderUnavailableError(ProviderError):
    pass


class ProviderSecurityError(ProviderError):
    pass


class ProviderConfigurationError(ProviderError):
    pass


@dataclass(frozen=True)
class UploadConstraints:
    max_bytes: int
    max_duration_seconds: int
    allowed_mime_types: tuple[str, ...]
    cors_origin: str
    expires_in_seconds: int
    quality: str
    idempotency_key: str


@dataclass(frozen=True)
class UploadAuthorization:
    asset_id: str
    provider_upload_key: str
    upload_url: str
    expires_at: datetime


@dataclass(frozen=True)
class ProcessingSnapshot:
    state: ProcessingState
    reason_code: str | None = None


@dataclass(frozen=True)
class PlaybackGrant:
    url: str
    expires_at: datetime | None


@dataclass(frozen=True)
class AssetMetadata:
    byte_size: int | None
    sha256: str | None
    duration_seconds: float | None
    width: int | None
    height: int | None
    container: str | None
    video_codec: str | None
    audio_codec: str | None
    tracks: tuple[str, ...]


@dataclass(frozen=True)
class CaptionTrack:
    track_key: str
    language: str
    kind: str
    state: str


@dataclass(frozen=True)
class MasterExport:
    state: str
    url: str | None
    expires_at: datetime | None


@dataclass(frozen=True)
class DeletionReceipt:
    state: str
    requested_at: datetime | None
    verified_at: datetime | None


@dataclass(frozen=True)
class WebhookEvent:
    event_id: str
    occurred_at: datetime
    kind: str
    provider_asset_key: str | None
    provider_upload_key: str | None
    provider_state: str | None
    raw_payload_sha256: str


class ManagedVideoProvider(Protocol):
    def create_upload_authorization(
        self, asset_id: str, constraints: UploadConstraints
    ) -> UploadAuthorization: ...

    def get_processing_state(self, provider_asset_key: str) -> ProcessingSnapshot: ...

    def resolve_review_playback(self, provider_asset_key: str, ttl: int) -> PlaybackGrant: ...

    def resolve_public_playback(self, provider_asset_key: str) -> PlaybackGrant: ...

    def attach_captions(
        self, provider_asset_key: str, language: str, vtt: str, idempotency_key: str
    ) -> CaptionTrack: ...

    def get_asset_metadata(self, provider_asset_key: str) -> AssetMetadata: ...

    def request_master_export(self, provider_asset_key: str, idempotency_key: str) -> MasterExport: ...

    def request_deletion(self, provider_asset_key: str, idempotency_key: str) -> DeletionReceipt: ...

    def verify_deletion(self, provider_asset_key: str) -> DeletionReceipt: ...

    def verify_webhook(
        self, headers: Mapping[str, str], raw_body: bytes, now: datetime
    ) -> WebhookEvent: ...


class FakeManagedVideoProvider:
    """Deterministic in-memory implementation for contract tests only."""

    _EVENT_MAP = {
        "video.upload.asset_created": "upload_completed",
        "video.asset.created": "asset_created",
        "video.asset.ready": "asset_ready",
        "video.asset.errored": "asset_failed",
        "video.asset.updated": "asset_updated",
        "video.asset.track.ready": "caption_ready",
        "video.asset.track.errored": "caption_failed",
        "video.asset.master.ready": "master_ready",
        "video.asset.master.errored": "master_failed",
        "video.asset.deleted": "asset_deleted",
    }

    def __init__(self, *, now: datetime, webhook_secret: bytes = b"contract-test-secret"):
        self.now = now.astimezone(timezone.utc)
        self._webhook_secret = webhook_secret
        self._uploads: dict[str, tuple[tuple[object, ...], UploadAuthorization]] = {}
        self._states: dict[str, ProcessingSnapshot] = {}
        self._metadata: dict[str, AssetMetadata] = {}
        self._public_assets: set[str] = set()
        self._captions: dict[str, tuple[tuple[object, ...], CaptionTrack]] = {}
        self._exports: dict[str, tuple[tuple[object, ...], MasterExport]] = {}
        self._deletions: dict[str, tuple[tuple[object, ...], DeletionReceipt]] = {}
        self._verified_event_ids: set[str] = set()

    def seed_asset(
        self,
        provider_asset_key: str,
        *,
        state: ProcessingState = ProcessingState.READY,
        metadata: AssetMetadata | None = None,
        public: bool = False,
    ) -> None:
        self._states[provider_asset_key] = ProcessingSnapshot(state)
        self._metadata[provider_asset_key] = metadata or AssetMetadata(
            byte_size=1024,
            sha256="0" * 64,
            duration_seconds=30.0,
            width=1080,
            height=1920,
            container="mp4",
            video_codec="h264",
            audio_codec="aac",
            tracks=("video", "audio"),
        )
        if public:
            self._public_assets.add(provider_asset_key)

    def mark_deleted(self, provider_asset_key: str) -> None:
        self._states[provider_asset_key] = ProcessingSnapshot(ProcessingState.DELETED)

    @staticmethod
    def _require_key(value: str, code: str) -> None:
        if not value or len(value) > 200 or not re.fullmatch(r"[A-Za-z0-9._:-]+", value):
            raise ProviderValidationError(code)

    @staticmethod
    def _idempotent(
        ledger: dict[str, tuple[tuple[object, ...], object]],
        key: str,
        fingerprint: tuple[object, ...],
        result: object,
    ) -> object:
        FakeManagedVideoProvider._require_key(key, "invalid_idempotency_key")
        prior = ledger.get(key)
        if prior:
            if prior[0] != fingerprint:
                raise ProviderConflictError("idempotency_conflict")
            return prior[1]
        ledger[key] = (fingerprint, result)
        return result

    def _require_asset(self, provider_asset_key: str) -> ProcessingSnapshot:
        self._require_key(provider_asset_key, "invalid_provider_asset_key")
        try:
            return self._states[provider_asset_key]
        except KeyError as exc:
            raise ProviderNotFoundError("asset_not_found") from exc

    def create_upload_authorization(
        self, asset_id: str, constraints: UploadConstraints
    ) -> UploadAuthorization:
        self._require_key(asset_id, "invalid_asset_id")
        if not 0 < constraints.max_bytes <= 2_000_000_000:
            raise ProviderValidationError("invalid_max_bytes")
        if not 0 < constraints.max_duration_seconds <= 180:
            raise ProviderValidationError("invalid_max_duration")
        if not constraints.allowed_mime_types or any(
            mime not in {"video/mp4", "video/quicktime"} for mime in constraints.allowed_mime_types
        ):
            raise ProviderValidationError("invalid_mime_types")
        if not re.fullmatch(r"https://[^/*\s]+", constraints.cors_origin):
            raise ProviderValidationError("invalid_cors_origin")
        if not 60 <= constraints.expires_in_seconds <= 900:
            raise ProviderValidationError("invalid_upload_expiry")
        if constraints.quality != "basic":
            raise ProviderValidationError("invalid_video_quality")
        fingerprint = (
            asset_id,
            constraints.max_bytes,
            constraints.max_duration_seconds,
            constraints.allowed_mime_types,
            constraints.cors_origin,
            constraints.expires_in_seconds,
            constraints.quality,
        )
        digest = hashlib.sha256(f"{asset_id}:{constraints.idempotency_key}".encode()).hexdigest()[:20]
        result = UploadAuthorization(
            asset_id=asset_id,
            provider_upload_key=f"fake-upload-{digest}",
            upload_url=f"https://upload.invalid/{digest}",
            expires_at=self.now + timedelta(seconds=constraints.expires_in_seconds),
        )
        return self._idempotent(self._uploads, constraints.idempotency_key, fingerprint, result)  # type: ignore[return-value]

    def get_processing_state(self, provider_asset_key: str) -> ProcessingSnapshot:
        return self._require_asset(provider_asset_key)

    def resolve_review_playback(self, provider_asset_key: str, ttl: int) -> PlaybackGrant:
        snapshot = self._require_asset(provider_asset_key)
        if snapshot.state != ProcessingState.READY:
            raise ProviderConflictError("asset_not_ready")
        if not 60 <= ttl <= 900:
            raise ProviderValidationError("invalid_playback_ttl")
        digest = hashlib.sha256(provider_asset_key.encode()).hexdigest()[:20]
        return PlaybackGrant(f"https://review.invalid/{digest}.m3u8", self.now + timedelta(seconds=ttl))

    def resolve_public_playback(self, provider_asset_key: str) -> PlaybackGrant:
        snapshot = self._require_asset(provider_asset_key)
        if snapshot.state != ProcessingState.READY or provider_asset_key not in self._public_assets:
            raise ProviderAuthorizationError("public_playback_not_enabled")
        digest = hashlib.sha256(provider_asset_key.encode()).hexdigest()[:20]
        return PlaybackGrant(f"https://stream.invalid/{digest}.m3u8", None)

    def attach_captions(
        self, provider_asset_key: str, language: str, vtt: str, idempotency_key: str
    ) -> CaptionTrack:
        snapshot = self._require_asset(provider_asset_key)
        if snapshot.state != ProcessingState.READY:
            raise ProviderConflictError("asset_not_ready")
        if not re.fullmatch(r"[a-z]{2,3}(?:-[A-Z]{2})?", language):
            raise ProviderValidationError("invalid_caption_language")
        if not vtt.startswith("WEBVTT\n") or len(vtt.encode()) > 1_000_000:
            raise ProviderValidationError("invalid_webvtt")
        fingerprint = (provider_asset_key, language, hashlib.sha256(vtt.encode()).hexdigest())
        digest = hashlib.sha256(":".join(fingerprint).encode()).hexdigest()[:20]
        result = CaptionTrack(f"fake-track-{digest}", language, "captions", "ready")
        return self._idempotent(self._captions, idempotency_key, fingerprint, result)  # type: ignore[return-value]

    def get_asset_metadata(self, provider_asset_key: str) -> AssetMetadata:
        self._require_asset(provider_asset_key)
        return self._metadata[provider_asset_key]

    def request_master_export(self, provider_asset_key: str, idempotency_key: str) -> MasterExport:
        self._require_asset(provider_asset_key)
        fingerprint = (provider_asset_key,)
        result = MasterExport("preparing", None, None)
        return self._idempotent(self._exports, idempotency_key, fingerprint, result)  # type: ignore[return-value]

    def request_deletion(self, provider_asset_key: str, idempotency_key: str) -> DeletionReceipt:
        self._require_asset(provider_asset_key)
        fingerprint = (provider_asset_key,)
        result = DeletionReceipt("requested", self.now, None)
        return self._idempotent(self._deletions, idempotency_key, fingerprint, result)  # type: ignore[return-value]

    def verify_deletion(self, provider_asset_key: str) -> DeletionReceipt:
        snapshot = self._require_asset(provider_asset_key)
        if snapshot.state != ProcessingState.DELETED:
            return DeletionReceipt("pending", None, None)
        return DeletionReceipt("verified", None, self.now)

    def verify_webhook(
        self, headers: Mapping[str, str], raw_body: bytes, now: datetime
    ) -> WebhookEvent:
        signature_header = next(
            (value for key, value in headers.items() if key.lower() == "mux-signature"), None
        )
        if not signature_header or len(raw_body) > 1_000_000:
            raise ProviderSecurityError("invalid_webhook_envelope")
        parts = dict(part.split("=", 1) for part in signature_header.split(",") if "=" in part)
        try:
            timestamp = int(parts["t"])
            supplied = parts["v1"]
        except (KeyError, ValueError) as exc:
            raise ProviderSecurityError("invalid_webhook_signature") from exc
        observed_now = now.astimezone(timezone.utc)
        occurred = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        if abs((observed_now - occurred).total_seconds()) > 300:
            raise ProviderSecurityError("stale_webhook")
        expected = hmac.new(
            self._webhook_secret, str(timestamp).encode() + b"." + raw_body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, supplied):
            raise ProviderSecurityError("invalid_webhook_signature")
        try:
            payload = json.loads(raw_body)
            event_id = payload["id"]
            event_type = payload["type"]
            data = payload.get("data") or {}
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ProviderSecurityError("invalid_webhook_payload") from exc
        self._require_key(event_id, "invalid_webhook_event_id")
        if event_id in self._verified_event_ids:
            raise ProviderSecurityError("replayed_webhook")
        self._verified_event_ids.add(event_id)
        kind = self._EVENT_MAP.get(event_type, "ignored")
        return WebhookEvent(
            event_id=event_id,
            occurred_at=occurred,
            kind=kind,
            provider_asset_key=data.get("id") if event_type.startswith("video.asset.") else data.get("asset_id"),
            provider_upload_key=data.get("upload_id") or (data.get("id") if event_type.startswith("video.upload.") else None),
            provider_state=data.get("status"),
            raw_payload_sha256=hashlib.sha256(raw_body).hexdigest(),
        )


def sign_fake_webhook(secret: bytes, timestamp: int, raw_body: bytes) -> str:
    """Create a synthetic signature for local contract fixtures."""

    signature = hmac.new(secret, str(timestamp).encode() + b"." + raw_body, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={signature}"
