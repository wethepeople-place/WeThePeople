# Phase 4D Mux pre-credential review and provider adapter design

Date: 2026-08-05

Status: Approved boundary for a network-free fake adapter; credentials, SDKs, provider resources, uploads, database changes, and production integration remain unauthorized

## Decision

Keep Mux Video Basic PAYG as the planned pilot provider, but do not create credentials or provider resources yet. Public Mux documentation supports the core workflow, while several account-specific, contractual, deletion, and malware questions remain unresolved.

Keep every uploaded source in application-owned quarantine until all validation gates pass. A Mux `ready` event means that Mux processed the media; it is not a malware-clearance result and cannot make a submission reviewable or public by itself.

Adopt the provider-neutral adapter described below. Its first implementation is an in-memory fake used only for contract tests. It performs no network access and contains no Mux dependency or secret.

## Dated official-document review

Reviewed on 2026-08-05:

- Mux's DPA states that Mux maintains technical and organizational safeguards, governs subprocessors, supports restricted-transfer mechanisms, and returns or deletes customer personal data subject to legal-retention exceptions. The public material does not establish a complete asset-by-asset backup purge deadline or a deletion certificate suitable for this pilot.
- Mux's security page directs customers to its Trust Center. Publicly accessible material is not enough to complete the planned review of current SOC reports, penetration-test detail, the complete live subprocessor inventory, or all processing locations. Those artifacts and any click-through DPA acceptance must be reviewed by the owner before credentials.
- Mux's terms make the customer responsible for account credentials and require prompt notice to Mux of unauthorized account use. Environment-scoped API tokens are supported. Least privilege, separate development and production environments, named human access, MFA, and removal of unused dashboard members remain required account controls.
- The DPA provides security-incident obligations, but the exact operational notification channel, escalation contacts, and any negotiated notification deadline should be recorded before production use.
- Mux Data processes IP addresses for coarse location and bot detection, then truncates them. Pseudonymized viewing data is retained for up to 100 days. EU IP processing is available by arrangement, while post-processed view data is sent to the United States. The pilot will disable the optional cross-page playback cookie, send no canonical user ID, and collect only operational playback data.
- Mux documentation and API references support resumable direct uploads, exact browser `cors_origin`, and upload URL timeout values from 60 seconds through 604,800 seconds. The application target remains 15 minutes.
- Direct uploads support chunked resume and gigabyte-scale files. The public documents reviewed do not state a definitive PAYG maximum file size or upload-concurrency quota. The 2 GB source limit and concurrent-session allowance therefore require written confirmation or a bounded account test after credentials are separately authorized.
- Mux assets may be up to 12 hours, so the application must enforce the pilot's three-minute maximum after trusted provider metadata is available. Client metadata is never authoritative.
- Video API rate limits are environment-scoped and expose limit/remaining headers. Current documented high-priority POST capacity is a 20-request bucket refilling at one request per second; exact account headers are authoritative at runtime. These API limits are not proof of upload-transfer concurrency.
- Direct-upload processing time varies with file characteristics. Mux publishes no deterministic processing SLA for this pilot. The application keeps its 30-minute processing timeout and permits only an explicit audited reconciliation to recover a late asset.
- Webhooks use HMAC-SHA256 over `timestamp.raw_body`, include an event ID, and default SDK verification tolerance is five minutes. The application will verify the raw body in constant time, enforce a five-minute maximum age, reject future-skewed or replayed event IDs, and tolerate duplicate/out-of-order delivery without applying publication transitions.
- Mux accepts SRT and WebVTT text tracks. The application canonical format is validated WebVTT; SRT may be converted before attachment. Human review remains required.
- Mux supports temporary master MP4 access for migration/offline archiving. Master URLs are short lived, server resolved, never public, and never stored as canonical identifiers.
- Mux exposes asset deletion and a deletion webhook. Application deletion is not complete until provider read-back returns not found (or an equivalent documented terminal result) on repeated reconciliation. Backup/subprocessor purge timing remains a contractual question.

## Unresolved questions that block credentials or uploads

1. Obtain or review the current Trust Center package, complete subprocessor list and locations, SOC report, and relevant penetration-test summary.
2. Record the controlling DPA version/acceptance, incident-notification route, account recovery process, and dashboard MFA/access configuration.
3. Obtain confirmation that PAYG direct upload accepts a 2 GB source and identify any per-environment transfer/concurrency quota.
4. Confirm deletion behavior for active assets, source/master copies, backups, CDN caches, and subprocessors, including normal and maximum purge timing and evidence available to the customer.
5. Confirm whether review playback can remain signed/private throughout processing and whether any provider metadata or preview is exposed outside the selected environment.
6. Approve and provision the malware control described below. Mux processing alone does not satisfy it.

No unresolved question is silently converted into an implementation assumption.

## Malware and media-validation gate: keep, replace, defer

### Keep

- Keep the contract's fail-closed malware gate and the separation between `processing` and `ready_for_creator_review`.
- Keep direct-to-provider upload so application servers do not accept 2 GB request bodies.
- Keep private-by-default playback, human moderation, checksum capture, strict duration/dimension checks, and deletion of failed or abandoned assets.

### Replace

Replace the ambiguous phrase "provider inspection" with a layered quarantine decision:

1. Before authorization, validate the declared byte size (maximum 2 GB), extension, MIME family, creator grant, active-draft limit, spend guard, and exact production web origin. These are preliminary controls only.
2. Issue one 15-minute authorization for an opaque asset ID. The resulting Mux asset has no public playback policy.
3. Treat every uploaded asset as quarantined. A Mux processing or ready event may populate technical metadata but cannot clear quarantine.
4. After processing, compare trusted duration, tracks, dimensions, and container/codec metadata with the contract. Reject extra attachments/tracks, unsupported formats/codecs, active content, malformed media, and limit mismatches.
5. Require a separate `media_safety=passed` result tied to the exact asset version and checksum. The production implementation must use either a reputable media/malware scanner that can examine the source without exposing it publicly, or a documented equivalent control approved by security. Scanner errors, timeouts, unsupported files, or unavailable results fail closed.
6. Only the application may transition from quarantine to `ready_for_creator_review`, after both technical validation and media-safety results pass. Editorial approval and publication remain later independent gates.
7. A failed result disables playback, records a non-sensitive reason code, preserves the minimum evidence needed for incident review, and schedules provider deletion. Creator-facing errors disclose no scanner signatures or security internals.

### Defer

- Defer selection or installation of a scanning vendor/tool, source-file export plumbing, and any scanner credentials until the owner approves the privacy, retention, cost, and threat-model tradeoff.
- Defer content classification, automated truth scoring, facial recognition, and automated final moderation. They do not satisfy the malware gate.
- Defer any claim that transcoding, MIME sniffing, or successful playback proves a source harmless.

This decision blocks the first real upload until a concrete scanning/equivalent control is approved and testable.

## Provider-neutral domain types

The adapter accepts and returns immutable values containing only opaque provider keys and the minimum operational data:

- `UploadConstraints`: byte limit, duration limit, allowed MIME types, exact CORS origin, expiry, quality, and idempotency key.
- `UploadAuthorization`: internal asset ID, opaque provider upload key, short-lived URL, and expiry. The URL is secret-equivalent and must be returned only to the authorized client; it is never logged, audited, persisted, or included in public APIs.
- `ProcessingSnapshot`: normalized `waiting`, `processing`, `ready`, `failed`, or `deleted` state plus a safe reason code.
- `PlaybackGrant`: normalized HLS URL and expiry for review, or a stable public playback locator after application publication. Administrative asset keys are not exposed.
- `AssetMetadata`: bytes/checksum when available, duration, dimensions, container, codecs, and tracks. Missing fields remain missing and fail their corresponding gate.
- `CaptionTrack`: provider-neutral track key, language, kind, and state.
- `MasterExport`: `preparing`, `ready`, `failed`, or `expired`, with a short-lived URL only while ready.
- `DeletionReceipt`: requested/verified timestamps and terminal state.
- `WebhookEvent`: provider event ID, occurred time, normalized event kind, opaque provider asset/upload key, normalized provider state, and raw-payload digest. Raw provider payloads are not domain events.

## Ten-operation adapter contract

Every provider implementation must implement exactly this public surface:

1. `create_upload_authorization(asset_id, constraints)`
2. `get_processing_state(provider_asset_key)`
3. `resolve_review_playback(provider_asset_key, ttl)`
4. `resolve_public_playback(provider_asset_key)`
5. `attach_captions(provider_asset_key, language, vtt, idempotency_key)`
6. `get_asset_metadata(provider_asset_key)`
7. `request_master_export(provider_asset_key, idempotency_key)`
8. `request_deletion(provider_asset_key, idempotency_key)`
9. `verify_deletion(provider_asset_key)`
10. `verify_webhook(headers, raw_body, now)`

The application service surrounding this interface owns authorization, draft/version checks, lifecycle transitions, moderation, audit events, retries, replay storage, reconciliation scheduling, and publication. The adapter never writes canonical video state and never decides that a video is public.

## Errors and retry rules

Adapters raise normalized errors with a safe code and no secret/provider body:

- `ProviderValidationError`: caller input violates the contract; never retry unchanged.
- `ProviderAuthenticationError`: credential missing/rejected; disable provider writes and alert; never expose credential data.
- `ProviderAuthorizationError`: environment/token lacks capability; configuration review required.
- `ProviderNotFoundError`: key is absent; terminal for reads and a possible successful deletion result only inside `verify_deletion`.
- `ProviderConflictError`: incompatible existing result or idempotency collision; reconcile before retry.
- `ProviderRateLimitedError`: retry after bounded provider guidance with jitter; freeze new authorizations if sustained.
- `ProviderUnavailableError`: timeout/5xx/network condition; bounded retry with jitter, then reconciliation.
- `ProviderSecurityError`: invalid/stale/replayed webhook or unsafe provider response; reject, audit safely, and do not retry as a trusted event.
- `ProviderConfigurationError`: unsupported account capability or unsafe adapter configuration; fail closed until corrected.

Unknown provider failures map to `ProviderUnavailableError` with an internal correlation ID. Provider response bodies, signed URLs, tokens, and headers never appear in user-facing errors or normal logs.

## Idempotency and reconciliation

- Every mutation uses an application-generated idempotency key scoped to operation, internal asset, and immutable version.
- Repeating a key with identical input returns the same normalized result. Reusing it with different input raises `ProviderConflictError`.
- Provider-native idempotency is used when available, but the application retains its own operation ledger because vendor guarantees may differ.
- Read operations are side-effect free. Reconciliation polls upload/asset state after missed or out-of-order webhooks and records observations before proposing an application transition.
- A webhook event ID is accepted at most once. Verification authenticates the envelope; application replay storage performs durable deduplication before effects.
- A provider `ready`, `errored`, or `deleted` event is an observation. It cannot skip the application state machine.
- Deletion is requested idempotently, playback is disabled immediately in the application, and a worker verifies provider absence. `deleted` is set only after terminal read-back; ambiguous failures remain `deletion_pending`.

## Webhook mapping

The Mux adapter may map only allowlisted events needed by the pilot:

| Provider event | Neutral kind | Permitted application effect |
|---|---|---|
| `video.upload.asset_created` | `upload_completed` | Correlate upload to opaque asset key; remain quarantined |
| `video.asset.created` | `asset_created` | Record observation only |
| `video.asset.ready` | `asset_ready` | Fetch metadata; remain quarantined |
| `video.asset.errored` | `asset_failed` | Propose processing failure for the matching version |
| `video.asset.updated` | `asset_updated` | Schedule reconciliation |
| `video.asset.track.ready` | `caption_ready` | Reconcile the matching caption track |
| `video.asset.track.errored` | `caption_failed` | Fail the matching accessibility gate |
| `video.asset.master.ready` | `master_ready` | Resolve a short-lived export only for an authorized migration job |
| `video.asset.master.errored` | `master_failed` | Mark export request failed |
| `video.asset.deleted` | `asset_deleted` | Schedule deletion read-back; do not mark deleted directly |

Unknown event types are authenticated and recorded as ignored observations; they do not mutate domain state. An uncorrelated event is quarantined for operator review.

## Cost-guard inputs

The adapter does not decide spend policy. It exposes or accepts provider-neutral observations used by a separate cost guard:

- stored asset count and stored minutes;
- monthly delivered minutes;
- active upload authorizations and projected new source minutes;
- current month metered cost, credit applied, tax excluded/included status, currency, observation time, and telemetry freshness;
- configured pilot ceilings: 20 published videos, 100 stored source minutes, 5,000 delivered minutes, USD 50 warning, USD 75 upload freeze, and USD 100 publication freeze.

Missing, stale, non-USD, or internally inconsistent billing telemetry freezes new upload authorization and publication until reconciled. Credits reduce expected invoice but never increase allowed usage.

## Secret and data boundaries

- Provider API token ID/secret, webhook secret, signing keys, and dashboard recovery material exist only in the server secret manager for one environment and purpose. They never enter repository files, client bundles, database rows, fixtures, logs, analytics, or chat.
- Signed upload, playback, and master URLs are ephemeral capabilities. Logs store only an internal correlation ID and URL type, never the value or query string.
- Provider metadata contains opaque internal correlation IDs only: no email, legal name, ZIP code, canonical user ID, evidence text, moderation notes, report data, or external social identity.
- Development and production use separate Mux environments, credentials, webhook secrets, and allowlisted origins. Production credentials cannot be used by tests or local development.
- The fake adapter uses deterministic non-routable/example URLs and synthetic keys. Contract tests reject accidental network use and require no environment variables.

## Fake-adapter acceptance criteria

The network-free contract suite must prove:

- all ten operations exist with the documented shapes;
- upload constraints fail closed and authorization is idempotent;
- review playback requires a ready asset and is short lived;
- public playback must be explicitly enabled in fake state rather than inferred from readiness;
- captions validate WebVTT/language and are idempotent;
- metadata and master export use provider-neutral states;
- deletion request is idempotent and verification is a separate terminal read;
- webhook verification checks HMAC, timestamp tolerance, event ID, allowlisted mapping, and replay rejection without applying publication state;
- normalized errors contain no secret or signed URL;
- no network, SDK, credentials, database, or production state is required.

## Stop gate

Passing the fake-adapter suite authorizes no Mux credential, environment, webhook, asset, upload, SDK installation, schema migration, runtime route, production configuration, or media publication. The owner must separately authorize least-privilege development credentials and one synthetic non-production upload after the unresolved questions and malware control are resolved.

## Official sources

- Mux DPA: https://www.mux.com/dpa
- Mux security and Trust Center entry: https://www.mux.com/security
- Mux terms: https://www.mux.com/terms
- Mux fundamentals and environment-scoped tokens: https://www.mux.com/docs/core/mux-fundamentals
- Direct uploads: https://www.mux.com/docs/guides/upload-files-directly
- Direct-upload API timeout and CORS: https://www.mux.com/docs/api-reference/video/direct-uploads/create-direct-upload
- API rate limits: https://www.mux.com/docs/core/make-api-requests
- Webhook signatures: https://www.mux.com/docs/core/verify-webhook-signatures
- Webhook lifecycle: https://www.mux.com/docs/core/listen-for-webhooks
- Webhook schema: https://www.mux.com/docs/webhook-reference
- Captions: https://www.mux.com/docs/guides/add-subtitles-to-your-videos
- Master access: https://www.mux.com/docs/guides/download-for-offline-editing
- Mux Data privacy: https://www.mux.com/docs/guides/ensure-data-privacy-compliance

Official product and legal materials were reviewed on 2026-08-05. Account-specific limits and contractual artifacts must be rechecked immediately before credentials are approved.
