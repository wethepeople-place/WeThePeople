# Phase 4D managed-video provider comparison

Date: 2026-08-05

Status: Mux selected for pilot planning; credentials, resources, and implementation deferred

## Recommendation

Choose **Mux Video on its pay-as-you-go plan** for the invitation-only Phase 4D pilot, using Basic on-demand quality, direct resumable uploads, signed playback during review, public or signed playback only after WeThePeople.place publication, human-reviewed captions, authenticated webhooks, and provider-neutral internal asset records.

Keep **Cloudflare Stream** as the documented fallback. It meets the core pilot requirements and has especially simple, predictable pricing, but Mux is the better fit for this small creator workflow because it combines a richer video-specific lifecycle, resumable direct uploads, free on-demand input, free generated captions, free hosted-video analytics, the first 100,000 delivery minutes free, and explicit temporary master-file access for migration/offline archiving.

This decision does not authorize signup, payment details, credentials, uploads, DNS, production resources, or runtime implementation.

## Contract envelope used for pricing

The calculation follows `CREATOR_VIDEO_CONTRACT.md` exactly:

- Up to 5 invited creators.
- Up to 20 published videos.
- Maximum 3 minutes per video, 1080p, and 2 GB source size.
- Maximum 100 source minutes stored.
- Maximum 5,000 delivered minutes per month.
- Hard provider ceiling: USD 100 per month.
- On-demand video only; no live streaming, DRM, custom media domain, AI workflows beyond captions, or paid support.

The 100-minute storage allowance is intentionally higher than 20 videos × 3 minutes (60 minutes) to cover drafts and replacement versions.

## Cost model

### Mux

Official list pricing for Basic on-demand video at 1080p:

- Input: free.
- Storage: USD 0.003 per stored minute per month.
- Delivery: first 100,000 delivered minutes per month free; then USD 0.001 per 1080p minute at the first paid tier.
- On-demand generated captions, Mux Player, signed URLs/domain restrictions, and Mux Data for Mux-hosted streams: listed as free.

Pilot maximum:

- Input: 100 minutes × USD 0 = **USD 0**.
- Storage: 100 minutes × USD 0.003 = **USD 0.30/month**.
- Delivery: 5,000 minutes, within the first 100,000 free minutes = **USD 0**.
- Modeled usage total: **USD 0.30/month** before taxes or optional features.

Mux's Free plan stores only 10 videos, so it cannot hold the 20-video pilot. The official pricing page says Pay As You Go has no storage limit and includes a USD 20 monthly usage credit. On 2026-08-05, the owner reviewed the live PAYG checkout, which stated USD 0 due today and end-of-cycle billing only for usage, plus applicable sales tax. The owner then enrolled the account in PAYG. The modeled USD 0.30 usage fits inside the listed USD 20 monthly credit, so the expected provider usage charge is USD 0 unless pricing, credit eligibility, taxes, or actual usage changes.

Stress check within the hard ceiling: after the free delivery allowance, USD 99.70 would buy about 99,700 additional 1080p delivery minutes at the first paid tier. The contract's 5,000-minute maximum is therefore far below the USD 100 guardrail.

### Cloudflare Stream

Official list pricing:

- Ingress and encoding: free.
- Storage: prepaid in USD 5 increments per 1,000 stored minutes.
- Delivery: USD 1 per 1,000 delivered minutes, post-paid.
- Bandwidth is included; no separate egress charge for Stream playback.

Pilot maximum:

- Storage usage: 100 minutes, but the minimum prepaid block is 1,000 minutes = **USD 5/month capacity purchase**.
- Delivery: 5,000 minutes ÷ 1,000 × USD 1 = **USD 5/month**.
- Modeled maximum total: **USD 10/month** before taxes.

At the stricter 60-minute published-library case, the bill remains USD 5 storage capacity plus actual delivery. Cloudflare is still well below the USD 100 ceiling, but its minimum storage increment makes it more expensive than Mux at this pilot's scale.

### Cost conclusion

| Provider | Maximum modeled pilot cost | Billing caveat | Ceiling margin |
|---|---:|---|---:|
| Mux Basic PAYG | USD 0.30/month metered usage; expected to be covered by the USD 20 credit | Live checkout confirmed USD 0 today and usage-only end-of-cycle billing; monitor taxes and term changes | USD 99.70 |
| Cloudflare Stream | USD 10/month | USD 5 prepaid storage block plus post-paid delivery | USD 90 |

Neither provider requires anything close to USD 100 for the approved pilot envelope. The ceiling remains a kill-switch threshold, not a budget target.

## Requirements comparison

| Contract requirement | Mux | Cloudflare Stream | Decision |
|---|---|---|---|
| Direct creator upload without client API credentials | Direct Upload creates an authenticated URL; client upload is resumable | Direct Creator Upload creates a one-time URL; TUS is required over 200 MB and recommended for unreliable links | Both pass; use resumable upload for every pilot file |
| 2 GB source files | Resumable direct upload supports large files; exact account limits must be confirmed | TUS supports large files and Stream accepts files under 30 GB | Both pass; Cloudflare documents the limit more explicitly |
| 3-minute server-side duration bound | Application must enforce; upload URL timeout and asset metadata support reconciliation | `maxDurationSeconds` reserves/enforces duration for direct uploads | Cloudflare advantage; application enforcement remains mandatory for either |
| Adaptive 1080p playback | HLS/adaptive playback with Basic quality up to 4K | H.264 adaptive playback from 360p to 1080p | Both pass |
| Private review playback | Signed playback IDs/URLs plus domain/referrer restrictions | `requireSignedURLs`, expiring tokens, allowed origins, and geo/IP rules | Both pass |
| Captions/transcript | SRT and WebVTT, multiple tracks, free generated on-demand captions, VTT and plain-text transcript access | WebVTT upload/generation/list/delete APIs; one track per language and 10 MB caption limit | Mux advantage for SRT ingestion and transcript workflow; both satisfy pilot accessibility |
| Authenticated processing callbacks | Signed webhooks with documented verification | HMAC-SHA256 signed webhook, timestamp/replay guidance, ready/error states | Both pass; application idempotency and ordering are still required |
| Deletion and reconciliation | Asset deletion API/CLI; application must verify disappearance | Delete video API/binding; deleted videos stop consuming storage | Both pass; neither replaces local deletion reconciliation |
| Portability/vendor exit | Temporary 24-hour master MP4 access explicitly supports moving videos to another service | MP4 downloads can be generated and secured; delivery minutes are billed | Mux advantage for explicit master-access migration workflow |
| Playback protection | Signed URLs, domain/referrer controls listed free; DRM costs USD 100/month and is out of scope | Signed URLs, allowed origins, IP/geo restrictions | Both pass; no DRM for pilot |
| Analytics | Mux Data included for hosted streams; 100-day view-data retention documented | Server-side dashboard/GraphQL analytics; maximum retention 90 days | Both pass; collect only operational counts and avoid behavioral profiles |
| Provider-neutral integration | Strong API/webhook asset model | Strong API/webhook video model | Both pass if internal IDs remain canonical |
| Pricing predictability | Lowest modeled cost, but PAYG billing terms need confirmation | Simplest formula and known USD 5 storage minimum | Mux wins cost; Cloudflare wins simplicity |

## Unresolved blockers and evidence gaps

- Neither reviewed product documentation establishes built-in malware scanning suitable for the contract's malware gate. Before implementation, approve a quarantine/scanning design or amend the gate with equivalent documented media-validation controls. Direct-upload completion alone is not a clean malware result.
- Mux's reviewed documentation establishes resumable direct upload but did not provide a definitive self-service file-size/concurrency limit for the PAYG account. Confirm that the 2 GB contract limit is supported before credential or resource approval.
- Neither public product guide is sufficient proof of backup-purge timing or complete deletion from subprocessors. Confirm deletion commitments and lawful-hold behavior through the then-current DPA, privacy terms, and support response.
- The live Mux PAYG checkout resolved the minimum-charge question for enrollment by stating USD 0 due today and usage-only end-of-cycle billing. Pricing, credit eligibility, tax treatment, and checkout terms must still be rechecked before future plan changes.
- Cloudflare's prepaid storage purchase is clear, but taxes, currency conversion, and account-wide interactions with existing Cloudflare services are outside this model.

These gaps block credential creation, provider resources, or implementation; they do not reverse the Mux selection for pilot planning.

## Security and privacy findings

### Shared implementation rules

- Keep provider API tokens server-side in a secret manager and issue only one-purpose upload URLs to clients.
- Default review assets to signed/private playback and explicitly change exposure only after application publication.
- Bind upload authorization to internal creator, draft, version, size, duration, MIME family, expiry, and idempotency key.
- Verify webhook signatures in constant time, reject stale timestamps/replays, store provider event IDs, and tolerate duplicate/out-of-order events.
- Never send legal name, email, ZIP code, evidence text, moderation notes, reporter data, or TikTok identity as provider metadata. Use opaque internal correlation IDs.
- Disable or minimize optional viewer analytics identifiers. Do not send a stable canonical `users.id` to either analytics product.
- Execute the provider DPA/security review and record subprocessors/data locations before production.
- Reconcile deletion through provider read-back; a local database flag is insufficient.

### Mux-specific notes

- Mux documents a DPA and states Mux Data processes IP address for coarse location/bot detection, truncates it, and retains pseudonymized view data for up to 100 days.
- Mux Data can use a generated anonymous viewer ID and its first-party playback cookie can be disabled. The pilot should disable cross-page playback cookies unless a narrowly documented need is approved.
- Do not enable paid DRM, custom domains, premium/plus encoding, Robots moderation, translation, summarization, or other AI jobs in the pilot.
- Use Basic quality and explicit `cors_origin`; never use wildcard CORS in production upload authorization.

### Cloudflare-specific notes

- Stream's signed tokens can expire no more than 24 hours in the future and can combine allowed origins with IP/geo restrictions.
- Cloudflare analytics can group by a supplied creator identifier and retain data for up to 90 days. Use an opaque rotating/non-personal creator reference or omit it unless cost operations require it.
- TUS upload reservations consume the configured maximum duration until completion or expiry. Keep one active upload authorization per draft and use short expiry to prevent quota exhaustion.
- Cloudflare's customer DPA and Trust Hub must be included in the pre-production legal/security review.

## Provider adapter boundary

Implementation must expose an internal interface rather than importing provider concepts throughout the product:

1. `create_upload_authorization(asset_id, constraints)`
2. `get_processing_state(provider_asset_key)`
3. `resolve_review_playback(provider_asset_key, ttl)`
4. `resolve_public_playback(provider_asset_key)`
5. `attach_captions(provider_asset_key, language, vtt)`
6. `get_asset_metadata(provider_asset_key)`
7. `request_master_export(provider_asset_key)`
8. `request_deletion(provider_asset_key)`
9. `verify_deletion(provider_asset_key)`
10. `verify_webhook(headers, raw_body)`

Provider payloads map into application-owned states; they never directly change `publication_state`. Tests must run against a fake adapter and contract fixtures before any provider sandbox test.

## Keep / replace / defer

### Keep

- Keep the Phase 4D contract, canonical application IDs, state machine, human moderation, evidence graph, privacy/export/deletion rules, audit events, kill switches, and USD 100 ceiling.
- Keep both provider implementations conceptually replaceable behind one adapter.
- Keep Cloudflare Stream as the fallback if Mux PAYG terms, privacy review, or implementation testing produces a blocker.

### Replace

- Replace the contract's unresolved `production_provider` placeholder with **Mux Basic PAYG** only after signup/payment terms and DPA/security review are approved.
- Replace durable public media URLs in application records with opaque provider keys and server-resolved playback data.
- Replace provider dashboards as operational truth with reconciled application records and immutable audit events.

### Defer

- Cloudflare Stream implementation, unless the Mux approval gate fails.
- Live video, DRM, custom media domains, MP4 public downloads, watermarking, premium encoding, paid AI workflows, viewer-level analytics, and more than one provider in production.
- TikTok Share Kit/Direct Post, which remains downstream of the independent canonical creator pilot.

## Approval gates before credentials or provider resources are created

1. Treat PAYG enrollment as complete; do not change plans without rechecking pricing, credits, taxes, and recurring terms.
2. Review Mux's then-current DPA, security materials, subprocessor list, data locations, deletion behavior, incident terms, and account-level access controls.
3. Confirm exact direct-upload file, duration, timeout, and concurrency limits for the PAYG account.
4. Approve the proposed privacy posture: private-by-default review playback, wildcard CORS forbidden, optional viewer cookie disabled, no direct personal identifiers in provider metadata.
5. Approve a cost monitor at USD 50 warning, USD 75 upload freeze, and USD 100 hard publication freeze. These controls require current usage data and must fail safely if billing telemetry is unavailable.
6. Approve the provider adapter design and fake-adapter contract tests before provider SDK installation.
7. Keep production creator/upload/publication feature flags off until the full Phase 4D launch gates pass.

## Official sources reviewed

### Mux

- Pricing: https://www.mux.com/pricing
- Pricing model: https://www.mux.com/docs/pricing/overview
- Direct uploads: https://www.mux.com/docs/guides/upload-files-directly
- Direct-upload API: https://www.mux.com/docs/api-reference/video/direct-uploads/create-direct-upload
- Webhook verification: https://www.mux.com/docs/core/verify-webhook-signatures
- Captions and subtitles: https://www.mux.com/docs/guides/add-subtitles-to-your-videos
- Generated captions/transcripts: https://www.mux.com/docs/guides/add-autogenerated-captions-and-use-transcripts
- Master-file access/migration: https://www.mux.com/docs/guides/download-for-offline-editing
- Privacy guidance: https://www.mux.com/docs/guides/ensure-data-privacy-compliance
- Security: https://www.mux.com/security

### Cloudflare Stream

- Pricing: https://developers.cloudflare.com/stream/pricing/
- Direct creator uploads: https://developers.cloudflare.com/stream/uploading-videos/direct-creator-uploads/
- Resumable TUS uploads: https://developers.cloudflare.com/stream/uploading-videos/resumable-uploads/
- Supported uploads: https://developers.cloudflare.com/stream/uploading-videos/
- Webhook verification: https://developers.cloudflare.com/stream/manage-video-library/using-webhooks/
- Signed playback and allowed origins: https://developers.cloudflare.com/stream/viewing-videos/securing-your-stream/
- Captions: https://developers.cloudflare.com/stream/edit-videos/adding-captions/
- Video lifecycle API: https://developers.cloudflare.com/api/resources/stream/
- Analytics: https://developers.cloudflare.com/stream/getting-analytics/fetching-bulk-analytics/
- Customer DPA: https://www.cloudflare.com/cloudflare-customer-dpa/

Official documentation was reviewed on 2026-08-05. Pricing and product limits must be rechecked immediately before account approval because they can change.
