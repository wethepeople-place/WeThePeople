# Phase 4D verified-creator video contract

Date: 2026-08-05

Status: Proposed implementation boundary; provider selection and runtime implementation remain deferred

## Decision

Phase 4D may introduce a small, invitation-only workflow in which verified creators submit original civic videos for human review. WeThePeople.place remains the canonical system for creator authorization, civic-video identity, evidence linkage, moderation, publication state, playback state, privacy operations, and audit history.

The pilot must work without TikTok or any other social platform. A managed video provider may supply upload, malware-aware intake, transcoding, storage, adaptive playback, thumbnails, and delivery, but it must not decide who is a creator, whether a video is accurate or lawful, whether it is published, or how it is ranked.

No runtime route, database migration, upload UI, provider account, credential, DNS record, production resource, external post, or production Watch media enablement is authorized by this document.

## Pilot boundary

The first pilot is deliberately small:

- At most 5 invited creators.
- At most 5 active drafts per creator and 20 published pilot videos total.
- One original video file per submission; no stitched, remixed, live, or multi-asset posts.
- Maximum 3 minutes, 1080p, 30 frames per second, and 2 GB source file.
- MP4/MOV input with H.264 or HEVC video and AAC audio; the provider may normalize delivery formats.
- English captions or an English transcript are required for the pilot. Multilingual tracks are deferred, but the schema must not prevent them later.
- At least one primary civic issue and one official evidence source are required before review.
- Chronological/editorial ordering only. No behavioral ranking, advertising, monetization, public engagement counts, or creator payouts.
- Maximum planning envelope: 100 source minutes stored, 5,000 delivered minutes per month, and a hard provider spend ceiling of USD 100 per month. Any projected or actual breach disables new uploads and requires a new approval; it does not delete existing records.

The limits are product safety and cost controls, not promises to creators. They must be configurable server-side and enforce the more restrictive of application and provider limits.

## Keep

### Canonical identities and civic graph

Keep the existing `users.id` as the only account identity. Keep `videos.video_id` stable and preserve the existing relationships to `issues`, `bills`, `source_documents`, and `discussion_posts`. Existing public read routes and exact-video sharing remain backward compatible.

Keep civic evidence separate from creator narration. A creator caption, spoken claim, transcript, thumbnail, or external post is never an official source merely because it is attached to a video.

### Phase 4C delivery and accessibility rules

Keep the Phase 4C fail-closed rights, provenance, poster, transcript/caption, availability, and source-registry rules for official and publisher media. Creator-owned media adds a managed-hosted mode; it does not weaken those rules.

Keep one active player, pause on lost visibility/focus, manual play/pause, mute control, reduced-motion behavior, keyboard access, captions/transcript access, descriptive posters, explicit loading/empty/error/unavailable states, and context preservation when media fails.

### Authentication, privacy, and auditing

Keep the current login, session revocation, suspension, privacy export/anonymization, and immutable audit foundations. Raw provider credentials and upload tokens are never stored in a client bundle, repository, analytics event, or audit detail.

## Replace or extend

### Creator authorization

Do not overload the commercial `users.role` hierarchy (`free` through `admin`) with creator or editorial authority. Add separate, revocable capability records:

- `creator_grants`: user, status, scope, issuer, reason, issued/expiry/revoked timestamps.
- Allowed statuses: `invited`, `active`, `paused`, `revoked`.
- Pilot scope: `video:create`; later scopes require a new decision.
- An active, verified email and `creator_grants.status=active` are required to create or mutate a draft.
- Residence/document verification may be required by policy for a cohort, but must not be inferred from a paid tier or TikTok account.
- Suspension, account deactivation, expired grant, or revoked grant immediately blocks new upload sessions and draft mutation. Published records enter review; they are not silently deleted.

Editorial capabilities must also be separate from paid tiers:

- `video:review` for editorial, evidence, rights, safety, and accessibility review.
- `video:publish` for final publication and withdrawal.
- A creator cannot review or publish their own submission.
- The final publisher must differ from the creator and must be authorized at action time.
- A single pilot administrator may hold review and publish capabilities, but the audit must identify both decisions and an emergency withdrawal must receive retrospective second-person review within one business day.

### Provider-neutral media assets

Replace direct, durable provider URLs as canonical identifiers with provider-neutral records:

- `video_assets`: internal asset ID, video ID, asset kind, provider key, provider name, state, MIME type, byte size, duration, dimensions, checksum, created/updated timestamps, and deletion state.
- Asset kinds: `source_video`, `playback`, `poster`, `captions`.
- The database stores opaque provider keys, never signed upload/playback URLs.
- The server resolves short-lived upload authorization and playback data.
- Public responses expose only the delivery information needed by the client and never expose administrative provider identifiers or credentials.
- Provider webhooks are authenticated, replay-resistant, idempotent, ordered defensively, and mapped to internal asset IDs.
- Vendor migration must be possible without changing `video_id` or civic relationships.

### Creator submission record

Separate a mutable creator submission from the published public projection. The submission must include:

- Creator ID and creator-grant snapshot.
- Original filename only after sanitization; MIME type, byte size, SHA-256 checksum, duration, dimensions, and provider-neutral asset ID.
- Creator caption, transcript/caption track, language, content warning when applicable, poster/alt text, and AI-generated or materially altered disclosure.
- Primary issue, optional related bills, and official evidence source IDs.
- Rights holder, ownership/license attestation, music/audio attestation, people/location/privacy attestation, and source material disclosures.
- Moderation and accessibility review results, structured reasons, reviewer IDs, and timestamps.
- Version number so a material edit invalidates prior approvals.

Free-text moderation notes, reports, identity proof, provider payloads, and reviewer notes are private and must never appear in public video responses.

## Lifecycle and state machine

The application owns the state machine. Provider state cannot directly publish a video.

1. `draft` — metadata may be edited; no public visibility.
2. `upload_authorized` — one short-lived, single-purpose upload session exists.
3. `uploading` — bytes may be arriving; retry is safe and bounded.
4. `processing` — provider validation/transcoding is incomplete.
5. `processing_failed` — no review or publication; creator receives a safe error and retry path.
6. `ready_for_creator_review` — media, poster, metadata, and captions can be previewed exactly as submitted.
7. `submitted` — creator affirms the final preview and locks the reviewed version.
8. `in_review` — automated and human gates run; material edits return the record to `draft` and invalidate approvals.
9. `changes_requested` — private structured feedback is available to the creator.
10. `approved` — all required gates passed for this exact version; still not public.
11. `scheduled` — optional later state; disabled in the first pilot.
12. `published` — public projection is readable and playback is enabled.
13. `unlisted` — exact link works but the item is omitted from feeds; allowed only for incident response or pre-approved testing.
14. `rights_hold` — playback fails closed while civic context and permitted transcript/evidence remain.
15. `removed` — public playback and discovery are disabled after moderation or legal action; a neutral tombstone may remain.
16. `withdrawn` — creator-requested withdrawal; public playback and discovery are disabled while required audit/legal records remain.
17. `deletion_pending` — provider deletion requested and being reconciled.
18. `deleted` — provider assets verified deleted; retained metadata is minimized according to policy.

Every transition has an allowlist of source states, authorized actors, a reason code, timestamp, immutable audit event, and idempotency key. Invalid, skipped, stale-version, or duplicate transitions fail closed.

## Upload security and failure handling

- The API creates a draft before issuing upload authorization.
- Upload authorization is short lived (target 15 minutes), bound to one creator, draft, asset, content length, and allowed MIME family.
- Upload goes directly to the managed provider when supported; application servers do not proxy multi-gigabyte files.
- Filename, client MIME, and client duration are untrusted hints. Provider inspection and server-side metadata determine acceptance.
- Reject unsupported media, oversize files, duration/resolution violations, checksum mismatches, malware findings, and dangerous active content.
- Rate limits apply per account, IP risk signal, and creator grant. Concurrent upload sessions are bounded.
- Abandoned multipart uploads and failed assets are automatically deleted after a documented short retention window, targeted at 24 hours and never more than 7 days.
- Processing timeout target is 30 minutes. A timeout moves to `processing_failed`; late webhooks may recover only through an explicit, audited reconciliation transition.
- Webhook secrets are rotated, payloads are size-limited, signatures use constant-time verification, and replay IDs are retained long enough to reject duplicates.
- Provider outage leaves published civic metadata available with an unavailable-media state. It must not corrupt publication or moderation state.

## Publication gates

Publication fails closed unless every gate passes for the current immutable version:

1. Creator grant active and creator account not suspended.
2. Provider asset ready, checksum/duration/dimensions recorded, and playback verified.
3. Caption/transcript present, synchronized or reviewed, and accessible in web and mobile clients.
4. Poster is owned, licensed, creator-supplied, provider-derived under contract, or replaced by a text card; alt text is present.
5. Creator ownership/license, music/audio, privacy, and AI-alteration attestations complete.
6. No unresolved malware, safety, copyright, privacy, impersonation, or legal hold.
7. Primary issue exists and every cited evidence record is an approved HTTPS source.
8. Editorial narration and official evidence are separately labeled.
9. Editorial/factual-context, rights, safety/moderation, provenance, and accessibility reviews are approved.
10. Reviewer/publisher separation and authorization checks pass.
11. Exact public preview and deletion/withdrawal behavior have passed smoke tests.
12. Spend guard is healthy; a cost breach blocks new publication unless an authorized exception is recorded.

## Moderation, reports, takedowns, and appeals

The pilot is pre-moderated: nothing is public before review. Minimum review categories are illegal content, threats/harassment, hate or dehumanization, sexual/exploitative content, graphic violence, self-harm risk, dangerous misinformation context, impersonation/deceptive editing, doxxing/private information, copyright/music rights, and spam/manipulation.

Public video reports must accept a bounded reason and optional detail, deduplicate abusive repeats, rate limit reporters, protect reporter identity, and return no moderation internals. Reports enter a private queue with `open`, `reviewing`, `resolved`, or `dismissed` state.

Authorized staff need a one-action emergency withdrawal that immediately disables playback/discovery, records a reason, and preserves evidence. Provider deletion is a separate reconciled action so takedown does not wait on vendor deletion.

Creators may appeal a rejection, removal, or rights hold once per decision version. The appeal reviewer must differ from the original decision maker when staffing permits. Outcomes and reasons are audited; private reporter or reviewer information is not disclosed.

Target service levels for the pilot:

- Credible imminent-harm, doxxing, or illegal-content report: immediate withdrawal target, review within 4 hours.
- Copyright/privacy/impersonation claim: review within 1 business day.
- Ordinary safety or context report: review within 2 business days.
- Creator appeal: response within 5 business days.

These are operational targets, not guarantees or legal notice procedures. A designated legal/takedown contact and escalation path are required before launch.

## Privacy, retention, export, and deletion

The identity inventory and privacy export/anonymization services must be extended before pilot data exists.

- Classify creator grants and creator attestations as private identity/compliance data.
- Classify draft metadata, private review notes, reports, upload telemetry, provider asset keys, and webhook payloads explicitly.
- Do not collect government ID in the video workflow. If higher identity proof is later required, use the existing verification boundary and store only the minimum proof result/reference.
- Strip or normalize unnecessary source metadata, including precise geolocation, before publication. Warn creators not to upload private information.
- Published creator display labels must be deliberately chosen; legal names and emails are never inferred or exposed.
- Include creator submissions, grants, attestations, decisions, and public metadata in privacy export, excluding credentials, reporter identities, and protected moderation/security information.
- Account anonymization removes direct creator identifiers while preserving public civic records only when there is a documented lawful/contractual basis. Otherwise withdraw and delete the media.
- Creator withdrawal disables public playback promptly. Provider asset deletion target is 7 days, backups/provider purge target 30 days, subject to a documented legal hold.
- Failed/abandoned uploads: target 24 hours, maximum 7 days.
- Raw webhook payloads and upload diagnostics: maximum 30 days unless needed for an active incident.
- Private moderation and appeal records: 2 years, then delete or irreversibly minimize unless under legal hold.
- Security audit events: retain under the existing audit policy; minimize IP/user-agent/detail fields under the existing privacy rules.
- Provider deletion must be verified by callback or reconciliation job. A local `deleted` flag alone is insufficient.

## Audit events

At minimum record: grant invited/activated/paused/revoked; draft created; upload authorized/started/completed/failed/abandoned; provider processing state changed; metadata or evidence changed; creator preview affirmed; submitted; review opened; changes requested; each gate approved/rejected; published/unlisted/held/removed/withdrawn; report opened/resolved; appeal opened/resolved; provider deletion requested/confirmed/failed; consent for any external distribution; and cost guard tripped/cleared.

Audit details use stable internal IDs, version, reason code, actor/subject IDs, request correlation ID, and before/after state. They must not store tokens, signed URLs, raw media, full webhook bodies, unnecessary free text, or sensitive reporter information.

## Rollout and rollback

Rollout gates:

1. Provider comparison approved against this contract and the USD 100 monthly ceiling.
2. Threat model, privacy inventory, retention policies, and incident/takedown runbook reviewed.
3. Schema migration and downgrade/forward-recovery plan tested on a production-shaped backup.
4. Provider adapter contract tests and webhook replay/idempotency tests pass.
5. Web and mobile creator preview, captions, moderation, report, withdrawal, and deletion flows pass accessibility and failure-mode tests.
6. Kill switches default off and are documented.
7. One internal synthetic creator completes the workflow in a non-production environment.
8. Production begins with one invited creator and one unlisted video; public publication requires explicit launch approval.

Required kill switches:

- Disable new creator grants.
- Disable new upload authorizations.
- Disable submission/review transitions.
- Disable publication while retaining drafts.
- Mark managed playback unavailable without deleting civic records.
- Disable each external distribution adapter independently.

Rollback never deletes records automatically. First disable new writes/publication, preserve audit evidence, withdraw affected playback when necessary, reconcile provider assets, and use a reviewed forward migration or restore procedure. Existing Phase 4C official/link-out records and public read routes must continue working if the creator workflow is disabled.

## Defer

Defer camera recording/editing, live streaming, duets/remixes, public creator enrollment, self-publication, direct messages, public follower/like/view counts, comments specific to the creator workflow, creator monetization, advertisements, behavioral recommendations, face recognition, automated truth scoring, automated final moderation decisions, multilingual transcription, bulk imports, external network ingestion, and creator analytics beyond minimal operational delivery counts.

TikTok Login, OpenSDK, Share Kit, and Direct Post remain optional distribution work governed by the dated `PHASE_4D_TIKTOK_INTEGRATION_DECISION.md` decision record in the project handoff workspace. They cannot bypass this workflow or become canonical identity, storage, moderation, publication, or audit systems. That decision record should move into this repository beside the contract before TikTok implementation begins.

## Acceptance tests required before implementation can launch

- Authorization: non-creators cannot create drafts; expired/revoked/suspended creators cannot upload; paid tier alone grants nothing.
- Isolation: one creator cannot read or mutate another creator's drafts or upload authorization.
- Upload: expired, replayed, oversized, wrong-type, corrupt, and duplicate callbacks fail safely.
- State machine: invalid, stale-version, skipped, and duplicate transitions fail closed and remain auditable.
- Separation: creator cannot review/publish own submission; unauthorized reviewer/publisher fails.
- Publication: every missing rights, evidence, transcript/caption, accessibility, safety, privacy, or review field blocks publication.
- Privacy: no credential/signed URL/private note/reporter identity appears in public APIs, logs, exports, or analytics.
- Accessibility: keyboard, screen reader, reduced motion, captions/transcript, poster alt text, focus/visibility, and media failure behavior pass on web and mobile.
- Moderation: report, emergency withdrawal, rights hold, appeal, and neutral tombstone preserve permitted civic context.
- Deletion: withdrawal is immediate; provider deletion is idempotent, reconciled, retryable, and verified.
- Cost: configured asset/minute/count ceilings stop new upload or publication without disrupting existing playback.
- Resilience: provider outage and delayed/out-of-order/replayed webhooks do not publish or corrupt records.
- Compatibility: Phase 4C records, stable `video_id`, existing public read routes, issue/bill/evidence/discussion links, and deterministic ordering remain intact.

## Next decision

Compare Mux and Cloudflare Stream only against this contract. The comparison must use current official pricing and product/security documentation, calculate the bounded pilot envelope, identify hard blockers and implementation differences, and recommend keep/replace/defer with an explicit worst-case monthly cost. Research does not authorize signup, credentials, DNS, uploads, or production resources.
