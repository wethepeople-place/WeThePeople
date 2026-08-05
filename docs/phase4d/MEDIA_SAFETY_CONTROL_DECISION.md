# Phase 4D media-safety control decision

Date: 2026-08-05

Status: Selected pre-credential design boundary; provisioning and runtime implementation remain separately authorized

## Decision

Use a private Cloudflare R2 Standard bucket as application-owned source quarantine, followed by an isolated ClamAV and media-validation worker. Mux may ingest the exact quarantined object only after the application records a passing result tied to that object's immutable version and SHA-256 checksum.

This replaces direct browser-to-Mux upload for untrusted creator source files. The browser still uploads directly to managed object storage, so the application API never proxies a multi-gigabyte body. Mux remains the managed transcoding, playback, and delivery provider; it does not perform or decide malware clearance.

No R2 bucket, token, scanner, Mux credential, environment, webhook, asset, upload, schema, route, deployment, or production configuration is authorized by this decision.

## Why this control

- It examines the exact bytes supplied by the creator before Mux receives them.
- R2 supports objects far larger than the pilot's 2 GB ceiling and supports resumable multipart uploads.
- The quarantine bucket remains non-public. Short-lived operation-specific URLs are bearer capabilities and are never logged or persisted.
- ClamAV is self-hosted, uses signed official signature databases, and sends no creator media to a scanning vendor.
- Strict container/codec parsing complements signature scanning; neither successful transcoding nor MIME sniffing is treated as malware clearance.
- The pilot's expected R2 storage and operation volume fits inside the published Standard free allowance, but all usage still counts against the existing spend guard.

## Source-access path

1. The application creates the draft and immutable source-asset version before upload.
2. After creator, draft, size, type, concurrency, origin, and spend checks, the server creates a 15-minute, single-object upload capability for an opaque R2 key. The bucket is private and its CORS allowlist contains only the exact approved application origin.
3. The client uploads directly to R2 using resumable multipart upload. The application server never receives the body.
4. Completion is accepted only after R2 read-back confirms the expected object key, exact byte count, and supplied checksum. Multipart ETags are not checksums.
5. An isolated worker reads the private object, calculates SHA-256, scans it with ClamAV using current official signed signatures, and performs bounded media parsing. The worker runs as an unprivileged user with read-only source access, ephemeral scratch space, CPU/memory/time limits, no inbound network listener, and no general outbound access.
6. Media parsing must confirm one allowed video stream, at most one allowed audio stream, no unexpected attachments/data tracks, an allowlisted MP4/MOV container, H.264 or HEVC video, AAC audio when audio is present, and the pilot duration/dimension/frame-rate limits. Parsing occurs in a sandboxed subprocess and never renders active content.
7. `media_safety=passed` is recorded only when checksum, signature freshness, ClamAV, parser, and all limits pass for the same immutable asset version. Any mismatch, skipped data, exceeded scan limit, stale signature database, timeout, parser crash, unsupported structure, encrypted content, or unavailable dependency fails closed.
8. Only after that result may the server issue Mux a short-lived read capability for the same object and request ingest. The capability permits only that object and expires as soon as practical. The object remains quarantined until Mux readiness and checksum/version correlation are reconciled.
9. Mux readiness still cannot publish. The application must separately pass captions, rights, privacy, moderation, evidence, accessibility, editorial, and publication gates.

## Privacy and retention

- The R2 bucket is never public and has no public development domain or custom domain.
- Object keys contain opaque internal identifiers only: no name, email, filename, ZIP code, civic evidence text, or social identity.
- Upload, read, and delete capabilities are secret-equivalent. Their values and query strings never enter logs, analytics, audit details, fixtures, screenshots, or chat.
- The scanner stores only checksum, engine/signature versions, scan time, normalized verdict/reason, parser version, and validated technical metadata. It does not retain source bytes, extracted frames, audio, thumbnails, or scanner signature names in creator-facing records.
- Clean quarantine objects are deleted after successful Mux ingest reconciliation, targeted within 24 hours and never more than 7 days.
- Failed, abandoned, timed-out, or rejected objects are deleted within 24 hours where operationally possible, with a bucket lifecycle backstop of 7 days. Incomplete multipart uploads use a one-day abort target and never exceed 7 days.
- Scratch files are deleted at job completion and on startup recovery. No scratch data survives beyond 24 hours.
- Deletion is idempotent and verified by object read-back. A local database flag is not proof of deletion.
- A legal or security hold requires an explicit audited exception, restricted access, and a review/expiry date.

## Cost and capacity

- Use R2 Standard, not Infrequent Access, because quarantine is short-lived and Standard has no minimum storage duration or retrieval charge.
- Current published R2 Standard pricing is USD 0.015 per GB-month, USD 4.50 per million Class A operations, USD 0.36 per million Class B operations, and no Internet egress charge. The monthly free allowance is 10 GB-month, one million Class A operations, and ten million Class B operations.
- At the pilot maximum of twenty simultaneous 2 GB sources retained for one day, average storage is about 1.34 GB-month before retries, below the published storage allowance. Actual telemetry remains authoritative.
- Scanner capacity is not assumed free. ClamAV documents at least 3 GiB RAM and notes higher transient memory during signature reload. Provisioning must confirm isolated worker headroom without weakening the production API.
- Existing cost controls remain: warn at USD 50, freeze new uploads at USD 75, and freeze publication at USD 100. Missing or stale R2, scanner, or Mux cost telemetry freezes new upload authorization.

## Timeouts and failure behavior

- Upload authorization expires after 15 minutes; an already-started multipart session remains bounded by application session policy and the one-day abandonment target.
- Scan target: 15 minutes; hard ceiling: 30 minutes for a 2 GB pilot object. A timeout is not clean and moves the asset to a safe failed state.
- Signature age must be within 24 hours. Failed updates, corrupt databases, unsupported engine versions, or unknown signature age disable new scans and uploads.
- ClamAV must be configured so a 2 GB file is actually examined. A result that skipped the file or exceeded `MaxFileSize`, `MaxScanSize`, recursion, decompression, or scan-time limits is a failure, never a clean verdict.
- Parser or scanner disagreement, worker outage, malformed metadata, checksum mismatch, or a late result cannot clear quarantine automatically. Recovery requires an idempotent retry or explicit audited reconciliation.
- Infection or dangerous-content findings immediately disable review playback, store only a non-sensitive internal reason code, schedule R2 and any accidental Mux copy for deletion, and enter the incident-review path. Creator-facing text reveals no security signatures or internals.

## Network-free contract tests

Before any real upload, deterministic tests must prove:

- only the exact draft owner and immutable asset version receive an upload authorization;
- origin, expiry, size, MIME, checksum, replay, concurrency, and spend checks fail closed;
- multipart ETags are never accepted as SHA-256;
- scanner clean, infected, error, stale-signature, skipped-limit, timeout, and unsupported verdicts normalize safely;
- media parser accepts only the pilot container/codec/track limits and rejects active or unexpected content;
- a Mux ingest request is impossible until the exact checksum/version has both technical-validation and media-safety passes;
- duplicate and out-of-order completion, scan, ingest, and deletion events remain idempotent;
- signed URLs, credentials, raw media, scanner signatures, and private metadata never appear in logs, audit details, public APIs, or fixtures;
- clean, rejected, abandoned, and failed objects all reach verified deletion or remain visibly retryable in `deletion_pending`;
- no test needs R2, Mux, ClamAV, FFmpeg, credentials, environment variables, or network access.

Use the EICAR test string only inside an isolated synthetic test fixture when implementation is separately authorized. Never upload creator media for scanner validation.

## Acceptance and stop gate

This decision closes the pre-credential media-safety design gate. Together with the completed Mux assurance, account-MFA, and upload-limit gates, the planning prerequisites are complete.

The next action still requires separate explicit owner authorization. That authorization must separately scope any development-only R2 bucket/token, isolated scanner provisioning, Mux development environment/token, webhook, SDK installation, schema/runtime work, and one synthetic non-production upload. Production creator/upload/publication flags, Watch embeds, the Census pilot, and TikTok integration remain off.

## Official sources reviewed

- Cloudflare R2 limits: https://developers.cloudflare.com/r2/platform/limits/
- Cloudflare R2 uploads: https://developers.cloudflare.com/r2/objects/upload-objects/
- Cloudflare R2 presigned URLs: https://developers.cloudflare.com/r2/api/s3/presigned-urls/
- Cloudflare R2 CORS: https://developers.cloudflare.com/r2/buckets/cors/
- Cloudflare R2 lifecycle rules: https://developers.cloudflare.com/r2/buckets/object-lifecycles/
- Cloudflare R2 pricing: https://developers.cloudflare.com/r2/pricing/
- ClamAV overview and requirements: https://docs.clamav.net/
- ClamAV scanning: https://docs.clamav.net/manual/Usage/Scanning.html
- ClamAV signature management: https://docs.clamav.net/manual/Usage/SignatureManagement.html

Official materials were reviewed on 2026-08-05. Recheck product limits, prices, scanner support, signature health, and host capacity before provisioning.
