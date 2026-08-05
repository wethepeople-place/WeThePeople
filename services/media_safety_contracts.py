"""Network-free Phase 4D quarantine and media-safety domain contracts.

This module contains immutable values, protocols, an in-memory quarantine fake,
and a fail-closed safety gate. It has no provider SDK, environment lookup,
database access, route registration, subprocess, or network behavior.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Protocol


MAX_SOURCE_BYTES = 2_000_000_000
MAX_DURATION_SECONDS = 180.0
MAX_WIDTH = 1920
MAX_HEIGHT = 1920
MAX_FRAME_RATE = 30.0
MAX_SIGNATURE_AGE = timedelta(hours=24)
MAX_SCAN_SECONDS = 1_800
ALLOWED_MIME_TYPES = frozenset({"video/mp4", "video/quicktime"})
ALLOWED_CONTAINERS = frozenset({"mp4", "mov"})
ALLOWED_VIDEO_CODECS = frozenset({"h264", "hevc"})
ALLOWED_AUDIO_CODECS = frozenset({"aac", None})


class MediaSafetyError(Exception):
    """Base error with a stable, non-sensitive reason code."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class MediaSafetyValidationError(MediaSafetyError):
    pass


class MediaSafetyConflictError(MediaSafetyError):
    pass


class MediaSafetyNotFoundError(MediaSafetyError):
    pass


class ScannerVerdict(str, Enum):
    CLEAN = "clean"
    INFECTED = "infected"
    ERROR = "error"
    TIMEOUT = "timeout"
    UNSUPPORTED = "unsupported"
    STALE_SIGNATURES = "stale_signatures"
    SKIPPED_LIMIT = "skipped_limit"


class DeletionState(str, Enum):
    REQUESTED = "requested"
    PENDING = "pending"
    VERIFIED = "verified"


@dataclass(frozen=True)
class QuarantineConstraints:
    creator_id: str
    asset_id: str
    asset_version: int
    expected_bytes: int
    expected_sha256: str
    mime_type: str
    cors_origin: str
    expires_in_seconds: int
    active_uploads: int
    max_active_uploads: int
    spend_guard_healthy: bool
    idempotency_key: str


@dataclass(frozen=True)
class QuarantineAuthorization:
    creator_id: str
    asset_id: str
    asset_version: int
    object_key: str
    upload_url: str
    expires_at: datetime


@dataclass(frozen=True)
class QuarantineObservation:
    asset_id: str
    asset_version: int
    object_key: str
    byte_size: int
    sha256: str
    etag: str | None
    observed_at: datetime


@dataclass(frozen=True)
class ScannerResult:
    asset_id: str
    asset_version: int
    sha256: str
    verdict: ScannerVerdict
    engine_version: str
    signature_version: str
    signatures_updated_at: datetime
    scanned_bytes: int
    scan_seconds: int


@dataclass(frozen=True)
class MediaMetadata:
    asset_id: str
    asset_version: int
    sha256: str
    container: str
    video_codec: str
    audio_codec: str | None
    duration_seconds: float
    width: int
    height: int
    frame_rate: float
    tracks: tuple[str, ...]
    encrypted: bool = False
    active_content: bool = False


@dataclass(frozen=True)
class MediaSafetyDecision:
    asset_id: str
    asset_version: int
    sha256: str
    passed: bool
    reason_code: str
    decided_at: datetime


@dataclass(frozen=True)
class IngestGrant:
    asset_id: str
    asset_version: int
    sha256: str
    object_key: str
    read_url: str
    expires_at: datetime


@dataclass(frozen=True)
class QuarantineDeletionReceipt:
    object_key: str
    state: DeletionState
    requested_at: datetime | None
    verified_at: datetime | None


class QuarantineStore(Protocol):
    def create_upload_authorization(
        self, constraints: QuarantineConstraints
    ) -> QuarantineAuthorization: ...

    def record_completion(
        self, authorization: QuarantineAuthorization, observation: QuarantineObservation
    ) -> QuarantineObservation: ...

    def evaluate_media_safety(
        self,
        observation: QuarantineObservation,
        scanner: ScannerResult,
        metadata: MediaMetadata,
        now: datetime,
    ) -> MediaSafetyDecision: ...

    def create_ingest_grant(
        self, decision: MediaSafetyDecision, ttl_seconds: int
    ) -> IngestGrant: ...

    def request_deletion(
        self, object_key: str, idempotency_key: str
    ) -> QuarantineDeletionReceipt: ...

    def verify_deletion(self, object_key: str) -> QuarantineDeletionReceipt: ...


def _require_key(value: str, code: str) -> None:
    if not value or len(value) > 200 or not re.fullmatch(r"[A-Za-z0-9._:-]+", value):
        raise MediaSafetyValidationError(code)


def _require_sha256(value: str, code: str = "invalid_sha256") -> None:
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise MediaSafetyValidationError(code)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise MediaSafetyValidationError("timezone_required")
    return value.astimezone(timezone.utc)


class FakeQuarantineStore:
    """Deterministic in-memory quarantine fake using non-routable URLs."""

    def __init__(self, *, now: datetime):
        self.now = _utc(now)
        self._uploads: dict[str, tuple[tuple[object, ...], QuarantineAuthorization]] = {}
        self._authorizations: dict[str, QuarantineAuthorization] = {}
        self._observations: dict[str, QuarantineObservation] = {}
        self._decisions: dict[tuple[str, int, str], MediaSafetyDecision] = {}
        self._deletions: dict[str, tuple[tuple[object, ...], QuarantineDeletionReceipt]] = {}
        self._deleted: set[str] = set()

    @staticmethod
    def _idempotent(
        ledger: dict[str, tuple[tuple[object, ...], object]],
        key: str,
        fingerprint: tuple[object, ...],
        result: object,
    ) -> object:
        _require_key(key, "invalid_idempotency_key")
        prior = ledger.get(key)
        if prior:
            if prior[0] != fingerprint:
                raise MediaSafetyConflictError("idempotency_conflict")
            return prior[1]
        ledger[key] = (fingerprint, result)
        return result

    def create_upload_authorization(
        self, constraints: QuarantineConstraints
    ) -> QuarantineAuthorization:
        _require_key(constraints.creator_id, "invalid_creator_id")
        _require_key(constraints.asset_id, "invalid_asset_id")
        _require_sha256(constraints.expected_sha256)
        if constraints.asset_version < 1:
            raise MediaSafetyValidationError("invalid_asset_version")
        if not 0 < constraints.expected_bytes <= MAX_SOURCE_BYTES:
            raise MediaSafetyValidationError("invalid_source_size")
        if constraints.mime_type not in ALLOWED_MIME_TYPES:
            raise MediaSafetyValidationError("invalid_mime_type")
        if not re.fullmatch(r"https://[^/*\s]+", constraints.cors_origin):
            raise MediaSafetyValidationError("invalid_cors_origin")
        if not 60 <= constraints.expires_in_seconds <= 900:
            raise MediaSafetyValidationError("invalid_upload_expiry")
        if constraints.max_active_uploads < 1 or constraints.active_uploads < 0:
            raise MediaSafetyValidationError("invalid_upload_concurrency")
        if constraints.active_uploads >= constraints.max_active_uploads:
            raise MediaSafetyConflictError("upload_concurrency_exceeded")
        if not constraints.spend_guard_healthy:
            raise MediaSafetyConflictError("spend_guard_unhealthy")

        fingerprint = (
            constraints.creator_id,
            constraints.asset_id,
            constraints.asset_version,
            constraints.expected_bytes,
            constraints.expected_sha256,
            constraints.mime_type,
            constraints.cors_origin,
            constraints.expires_in_seconds,
        )
        digest = hashlib.sha256(
            f"{constraints.asset_id}:{constraints.asset_version}:{constraints.idempotency_key}".encode()
        ).hexdigest()[:24]
        object_key = f"development/quarantine/{digest}"
        result = QuarantineAuthorization(
            creator_id=constraints.creator_id,
            asset_id=constraints.asset_id,
            asset_version=constraints.asset_version,
            object_key=object_key,
            upload_url=f"https://upload.invalid/{digest}",
            expires_at=self.now + timedelta(seconds=constraints.expires_in_seconds),
        )
        authorized = self._idempotent(
            self._uploads, constraints.idempotency_key, fingerprint, result
        )
        self._authorizations[object_key] = authorized  # type: ignore[assignment]
        return authorized  # type: ignore[return-value]

    def record_completion(
        self, authorization: QuarantineAuthorization, observation: QuarantineObservation
    ) -> QuarantineObservation:
        expected = self._authorizations.get(authorization.object_key)
        if expected != authorization:
            raise MediaSafetyConflictError("unknown_upload_authorization")
        if self.now > authorization.expires_at:
            raise MediaSafetyConflictError("upload_authorization_expired")
        _require_sha256(observation.sha256)
        if (
            observation.asset_id != authorization.asset_id
            or observation.asset_version != authorization.asset_version
            or observation.object_key != authorization.object_key
        ):
            raise MediaSafetyConflictError("upload_binding_mismatch")
        expected_bytes, expected_sha = self._expected_source_for(authorization)
        if observation.byte_size != expected_bytes:
            raise MediaSafetyConflictError("observed_size_mismatch")
        if observation.sha256 != expected_sha:
            raise MediaSafetyConflictError("checksum_mismatch")
        prior = self._observations.get(observation.object_key)
        if prior and prior != observation:
            raise MediaSafetyConflictError("completion_conflict")
        self._observations[observation.object_key] = observation
        return prior or observation

    def _expected_source_for(
        self, authorization: QuarantineAuthorization
    ) -> tuple[int, str]:
        for fingerprint, candidate in self._uploads.values():
            if candidate == authorization:
                return int(fingerprint[3]), str(fingerprint[4])
        raise MediaSafetyConflictError("unknown_upload_authorization")

    def create_ingest_grant(
        self, decision: MediaSafetyDecision, ttl_seconds: int
    ) -> IngestGrant:
        binding = (decision.asset_id, decision.asset_version, decision.sha256)
        if self._decisions.get(binding) != decision:
            raise MediaSafetyConflictError("media_safety_decision_not_recorded")
        if not decision.passed or decision.reason_code != "passed":
            raise MediaSafetyConflictError("media_safety_not_passed")
        if not 60 <= ttl_seconds <= 900:
            raise MediaSafetyValidationError("invalid_ingest_ttl")
        observation = next(
            (
                item
                for item in self._observations.values()
                if item.asset_id == decision.asset_id
                and item.asset_version == decision.asset_version
                and item.sha256 == decision.sha256
            ),
            None,
        )
        if observation is None:
            raise MediaSafetyConflictError("quarantine_source_not_verified")
        digest = hashlib.sha256(
            f"{observation.object_key}:{decision.sha256}".encode()
        ).hexdigest()[:24]
        return IngestGrant(
            asset_id=decision.asset_id,
            asset_version=decision.asset_version,
            sha256=decision.sha256,
            object_key=observation.object_key,
            read_url=f"https://read.invalid/{digest}",
            expires_at=self.now + timedelta(seconds=ttl_seconds),
        )

    def evaluate_media_safety(
        self,
        observation: QuarantineObservation,
        scanner: ScannerResult,
        metadata: MediaMetadata,
        now: datetime,
    ) -> MediaSafetyDecision:
        recorded = self._observations.get(observation.object_key)
        if recorded != observation:
            raise MediaSafetyConflictError("quarantine_source_not_verified")
        decision = MediaSafetyGate().decide(observation, scanner, metadata, now=now)
        binding = (decision.asset_id, decision.asset_version, decision.sha256)
        prior = self._decisions.get(binding)
        if prior and prior != decision:
            raise MediaSafetyConflictError("media_safety_decision_conflict")
        self._decisions[binding] = prior or decision
        return prior or decision

    def request_deletion(
        self, object_key: str, idempotency_key: str
    ) -> QuarantineDeletionReceipt:
        if object_key not in self._authorizations:
            raise MediaSafetyNotFoundError("quarantine_object_not_found")
        fingerprint = (object_key,)
        result = QuarantineDeletionReceipt(
            object_key, DeletionState.REQUESTED, self.now, None
        )
        return self._idempotent(
            self._deletions, idempotency_key, fingerprint, result
        )  # type: ignore[return-value]

    def mark_deleted(self, object_key: str) -> None:
        if object_key not in self._authorizations:
            raise MediaSafetyNotFoundError("quarantine_object_not_found")
        self._deleted.add(object_key)

    def verify_deletion(self, object_key: str) -> QuarantineDeletionReceipt:
        matching = next(
            (receipt for _, receipt in self._deletions.values() if receipt.object_key == object_key),
            None,
        )
        if matching is None:
            raise MediaSafetyConflictError("deletion_not_requested")
        if object_key not in self._deleted:
            return QuarantineDeletionReceipt(
                object_key, DeletionState.PENDING, matching.requested_at, None
            )
        return QuarantineDeletionReceipt(
            object_key, DeletionState.VERIFIED, matching.requested_at, self.now
        )


class MediaSafetyGate:
    """Fail-closed decision service for one immutable quarantine source."""

    def decide(
        self,
        observation: QuarantineObservation,
        scanner: ScannerResult,
        metadata: MediaMetadata,
        *,
        now: datetime,
    ) -> MediaSafetyDecision:
        decided_at = _utc(now)
        binding = (observation.asset_id, observation.asset_version, observation.sha256)
        if binding != (scanner.asset_id, scanner.asset_version, scanner.sha256):
            return self._failed(observation, "scanner_binding_mismatch", decided_at)
        if binding != (metadata.asset_id, metadata.asset_version, metadata.sha256):
            return self._failed(observation, "metadata_binding_mismatch", decided_at)
        if scanner.scanned_bytes != observation.byte_size:
            return self._failed(observation, "scan_size_mismatch", decided_at)
        if scanner.scan_seconds < 0 or scanner.scan_seconds > MAX_SCAN_SECONDS:
            return self._failed(observation, "scan_timeout", decided_at)
        signatures_updated_at = _utc(scanner.signatures_updated_at)
        if signatures_updated_at > decided_at or decided_at - signatures_updated_at > MAX_SIGNATURE_AGE:
            return self._failed(observation, "stale_signatures", decided_at)
        if scanner.verdict != ScannerVerdict.CLEAN:
            return self._failed(observation, f"scanner_{scanner.verdict.value}", decided_at)

        reason = self._validate_metadata(metadata)
        if reason:
            return self._failed(observation, reason, decided_at)
        return MediaSafetyDecision(
            observation.asset_id,
            observation.asset_version,
            observation.sha256,
            True,
            "passed",
            decided_at,
        )

    @staticmethod
    def _failed(
        observation: QuarantineObservation, reason: str, decided_at: datetime
    ) -> MediaSafetyDecision:
        return MediaSafetyDecision(
            observation.asset_id,
            observation.asset_version,
            observation.sha256,
            False,
            reason,
            decided_at,
        )

    @staticmethod
    def _validate_metadata(metadata: MediaMetadata) -> str | None:
        if metadata.encrypted:
            return "encrypted_media"
        if metadata.active_content:
            return "active_content"
        if metadata.container not in ALLOWED_CONTAINERS:
            return "unsupported_container"
        if metadata.video_codec not in ALLOWED_VIDEO_CODECS:
            return "unsupported_video_codec"
        if metadata.audio_codec not in ALLOWED_AUDIO_CODECS:
            return "unsupported_audio_codec"
        if not 0 < metadata.duration_seconds <= MAX_DURATION_SECONDS:
            return "invalid_duration"
        if not 0 < metadata.width <= MAX_WIDTH or not 0 < metadata.height <= MAX_HEIGHT:
            return "invalid_dimensions"
        if not 0 < metadata.frame_rate <= MAX_FRAME_RATE:
            return "invalid_frame_rate"
        if not metadata.tracks or metadata.tracks[0] != "video":
            return "invalid_tracks"
        if metadata.tracks not in {("video",), ("video", "audio")}:
            return "unexpected_tracks"
        return None
