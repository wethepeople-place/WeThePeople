# Phase 4D development provisioning plan

Date: 2026-08-05

Status: Read-only capacity decision and proposed provisioning sequence; no resource or credential creation authorized

## Decision

Do not run creator-media scanning on the production API server. When separately authorized, provision one isolated, disposable Hetzner CX33 development worker in Helsinki for the synthetic pilot, plus a private Cloudflare R2 Standard quarantine bucket and a separate Mux development environment.

Provisioning must occur in the phases below. Each phase has a verification and rollback point. No production creator, upload, publication, Watch, Census, or TikTok capability is enabled by this plan.

## Read-only production capacity finding

The live `wtp-api-prod` server was inspected read-only on 2026-08-05:

- 2 vCPU;
- 4,005,453,824 bytes RAM, no swap;
- approximately 3.10 GB memory available during the observation;
- approximately 34.78 GB disk available;
- `wtp-api` used about 291 MiB and `wtp-caddy` about 11 MiB during the observation;
- both production containers were healthy enough to report normal runtime statistics.

ClamAV's current guidance recommends at least 3 GiB RAM and notes that signature reload may transiently use about 2.4 GiB before file-processing memory. A 2 GB source scan, media parser, container runtime, operating system, API, and Caddy would have inadequate isolation margin on the 4 GB production host. Adding swap would not create acceptable fault isolation. Production capacity is therefore rejected for the scanner.

## Development worker envelope

Proposed Hetzner resource:

- name: `wtp-media-scan-dev`;
- project: existing `WeThePeople` project, development-tagged;
- location: Helsinki, matching production's EU-central location;
- type: CX33, shared resources, 4 vCPU, 8 GB RAM, 80 GB SSD;
- image: Ubuntu 24.04 LTS;
- backup: off because the worker is stateless and quarantine is in R2;
- public IPv4: include for the first bounded setup only if outbound/administrative connectivity cannot be satisfied safely without it;
- private network: attach a dedicated development network; do not attach production application data volumes or credentials;
- labels: `app=wethepeople`, `environment=development`, `purpose=media-scan`;
- deletion: destroy the worker after the synthetic validation period unless a later approval authorizes continued pilot operation.

Hetzner's current Finland price for a new CX33 is USD 0.016/hour with a USD 9.99 monthly server cap, excluding IPv4 and tax. A stopped server remains billable; cost stops only when the server is deleted. The development worker has a USD 15 monthly infrastructure ceiling including IPv4/tax estimate. A projected breach blocks creation or requires a new approval.

## Network boundary

- Default-deny inbound firewall.
- Permit SSH only from the owner's current administrative source range during setup, or through a separately approved private administrative path. Never allow public ClamAV, Docker, metrics, debug, or media-parser ports.
- The scanner exposes no application-facing public HTTP endpoint.
- Allow outbound DNS, operating-system/security updates, official ClamAV signature distribution, private R2 object access, Mux ingest retrieval, and the minimal health/telemetry destinations explicitly approved during implementation.
- Deny general outbound traffic from the scan job. Signature update runs separately from file-processing jobs so the untrusted-media parser has no network egress.
- R2 and Mux capabilities are single-object, operation-specific, short lived, and never logged.

## R2 development quarantine

Proposed Cloudflare resource:

- one private Standard bucket named with a non-production suffix selected at creation time;
- public access, `r2.dev`, and custom domains disabled;
- exact development application origin only in CORS;
- multipart upload for large video, with an application ceiling of 2 GB;
- opaque object keys containing no identity or filename;
- one-day incomplete-multipart abort target;
- deletion target within 24 hours and lifecycle backstop at seven days;
- server-side encryption at rest using the provider default; no public cache;
- least-privilege credentials separated by purpose: upload-session coordinator, scanner read/delete, and Mux-ingest read capability generation. No all-account token in runtime.

The bucket is not created until the final name, account, region behavior, CORS origin, lifecycle rule, and token scopes are displayed for owner approval. A read-back test must prove public access is denied before any object upload.

## Scanner services

Run separate constrained services rather than adding packages to the production API image:

1. `freshclam` update service with outbound access only to official signature distribution.
2. `clamd` on a Unix socket only, never TCP; current official signed databases only.
3. media-scan worker running unprivileged with a read-only root filesystem, no Docker socket, no host devices, no added Linux capabilities, `no-new-privileges`, bounded memory/CPU/PIDs, and ephemeral scratch storage.
4. sandboxed media parser using pinned FFmpeg/ffprobe packages; it reads but never executes or renders source content.
5. deletion reconciler with delete-only access to the exact development quarantine prefix.

Before scanning, effective ClamAV configuration must be captured without secrets and prove that `MaxFileSize`, `MaxScanSize`, stream length, recursion, decompression, and scan-time values do not skip a 2 GB source. Any limit-exceeded result is failure, not clean.

## Mux development boundary

- Use a new development environment distinct from any future production environment.
- Create one least-privilege API token only after the network-free adapter and orchestration tests pass.
- Limit the token to the minimum Video read/write capabilities required by the accepted ten-operation adapter; do not grant organization or billing administration.
- Use a separate webhook signing secret and exact development callback route.
- Keep playback private; no public playback policy is created by default.
- Provider metadata contains opaque internal correlation IDs only.
- Do not create the first Mux asset until R2 deletion, scanner failure, checksum binding, and webhook replay tests pass locally.

## Secret boundary

- No value enters Git, `.env.example`, database rows, container image layers, command history, logs, analytics, audit detail, screenshots, or chat.
- Separate credentials for R2 coordination, scanner access, Mux API, and Mux webhook verification.
- Deployment transport uses GitHub environment secrets only after environment protection is configured. Runtime delivery uses root-owned, service-specific credential files or encrypted systemd credentials mounted read-only into the intended service; secrets are not passed as Docker command-line arguments.
- Production and development credentials are never interchangeable.
- Record only secret identifiers, scope, owner, creation time, rotation due date, and revocation status.
- Rotate immediately after any suspected disclosure and revoke every development credential when the disposable worker is destroyed.

## Phased provisioning and stop points

### Phase A: network-free implementation

- Add provider-neutral quarantine, scanner-verdict, checksum-binding, and deletion-reconciliation domain contracts.
- Implement deterministic fakes and the accepted network-free tests.
- No R2/Mux SDK, token, environment variable, network request, database migration, or runtime route.
- Stop for review and green checks.

### Phase B: empty infrastructure

- Provision the isolated Hetzner worker and firewall.
- Create the empty private R2 development bucket, lifecycle, CORS, and least-privilege credentials.
- Install/pin scanner services and verify signature freshness, effective limits, sandbox, resource ceilings, logging redaction, and deletion behavior.
- Create the empty Mux development environment, least-privilege token, and webhook secret/route only if explicitly included in the authorization.
- Upload no object and create no Mux asset.
- Stop for read-only inspection and cost confirmation.

### Phase C: one synthetic validation

- Use one newly generated, non-personal, rights-clear, short synthetic video far below 2 GB.
- Verify checksum, clean result, parser metadata, Mux ingest, private review playback, webhook authentication/replay handling, R2 deletion, Mux deletion, and read-back reconciliation.
- Separately use isolated harmless negative fixtures for failure paths; never upload creator media or a live malware sample.
- Delete every synthetic object/asset and revoke one-time capabilities.
- Stop and report evidence. Production remains off.

## Rollback

- Phase A rollback is code-only and preserves no external state.
- Phase B rollback revokes R2/Mux tokens and webhook secret, deletes the empty Mux development resources and R2 bucket after read-back, destroys the stateless scanner worker, and verifies billing/resource inventory.
- Phase C rollback first disables new authorizations, deletes and verifies synthetic R2/Mux objects, revokes credentials, then destroys empty resources if directed.
- Never modify or delete the production API server, database, Caddy, DNS, Watch state, or existing Mux organization/account enrollment during rollback.

## Authorization required

This plan performs no provisioning. The next executable package needs explicit owner authorization naming the allowed phase. The recommended next authorization is **Phase A only: network-free implementation and tests**. It creates no vendor resource or credential and must merge before Phase B is considered.

## Official sources reviewed

- Hetzner current cloud pricing: https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/
- Hetzner regular-performance types: https://www.hetzner.com/cloud/regular-performance
- Hetzner cloud server overview: https://docs.hetzner.com/cloud/servers/overview/
- Cloudflare R2 limits: https://developers.cloudflare.com/r2/platform/limits/
- Cloudflare R2 uploads: https://developers.cloudflare.com/r2/objects/upload-objects/
- Cloudflare R2 presigned URLs: https://developers.cloudflare.com/r2/api/s3/presigned-urls/
- Cloudflare R2 CORS: https://developers.cloudflare.com/r2/buckets/cors/
- Cloudflare R2 lifecycle rules: https://developers.cloudflare.com/r2/buckets/object-lifecycles/
- ClamAV overview: https://docs.clamav.net/
- ClamAV scanning: https://docs.clamav.net/manual/Usage/Scanning.html
- ClamAV signature management: https://docs.clamav.net/manual/Usage/SignatureManagement.html

Official materials and live capacity were reviewed on 2026-08-05. Recheck price, availability, owner source IP, package versions, and account-specific scopes immediately before any Phase B action.
