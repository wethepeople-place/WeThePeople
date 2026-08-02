# Phase 4C Real Civic Video Feed decision

## Outcome

Phase 4C keeps the existing canonical Video identity, issue/bill/source relationships, read-only public endpoints, deterministic order, mobile vertical paging and visibility-based playback, transcript fallback, and exact-video canonical sharing. It repairs the parts that are still demonstration-only: a reviewed multi-item catalog, rights and provenance metadata, stable cursor pagination, a playable web feed, record-driven issue/evidence/bill/discussion navigation with return to the same video, provider-neutral media storage, and private editorial review.

This decision is network-free and non-operational. It adds no route, UI, job, model, migration, media asset, credential, upload surface, or publishing behavior.

## Audit inventory

The current `videos` model has a stable `video_id`, creator label, caption, optional transcript and captions URL, required direct media URL, one source, publication timestamp, and sort order. Link tables connect videos to issues and bills. Discussion attachments can reference a video, but Watch currently navigates only to the generic Discuss tab rather than an exact associated record.

The fixture loader is deliberately bounded to one Housing & Rent record and one reviewed bill. The public API exposes list, detail, share metadata, and an HTML preview. The list loads the whole catalog and has no cursor. Mobile has a full-height Expo feed with visibility, app-focus and reduced-motion playback gates, transcript display, share/copy actions, and unavailable/loading/empty/error states. Web has only a share-preview page and no playable feed. Direct external URLs are treated as media delivery. The only known video is the generic MDN flower sample; it is a development fallback and is not acceptance media.

No local rights-cleared civic video, caption, poster, or rights packet was found. The first implementation slice therefore remains blocked until three to five media packages are supplied or separately authorized. Rights, license, provenance, review, transcript, or accessibility facts must never be invented.

## Curated catalog contract

The first catalog contains three to five published videos. Every record keeps `video_id` as stable identity and has exactly one primary issue, one or more official evidence citations, zero or more related bills, and at most one associated discussion. Editorial narration and official evidence are visibly separate.

Publication fails closed unless the record has a rights basis (`owned`, `licensed`, or `public_domain`), rights holder and evidence reference, allowed uses, reviewer identity and time, provenance URL and retrieval time, transcript or captions, descriptive poster and alt text, duration, pixel dimensions and aspect ratio, publication and availability state, editorial review, accessibility review, and official evidence links. Missing or withdrawn media must not hide transcript, poster, provenance, official evidence, issue, bills, or discussion.

## Pagination and identity

The feed order is `(sort_order ASC, published_at DESC, video_id ASC)`. The cursor is an opaque, URL-safe, signed or authenticated encoding of a version plus that complete tuple. Default limit is 10 and maximum limit is 25. A response contains `videos`, `next_cursor`, and `has_more`. Invalid or tampered cursors fail with HTTP 400. Offset pagination is not accepted because inserts could duplicate or skip records. A snapshot-consistency mechanism must be chosen in the API slice and tested over multiple pages.

## Mobile and web parity

Both platforms must guarantee one active video, pause when hidden or inactive, manual play/pause and mute state, transcript or captions, reduced-motion behavior, descriptive posters, all unavailable/loading/empty/error states, exact-video sharing, and record-driven links to the exact issue, every official evidence source, each related bill, and the associated discussion. Returning restores the same `video_id`. Web additionally needs keyboard-operable controls and page/tab visibility handling.

## Editorial and storage boundary

Ingestion is private and authenticated. Editor, reviewer, and publisher are explicit roles; the reviewer differs from the submitter, and publication requires authorized publisher action plus rights, provenance, editorial, and accessibility review with an immutable audit event. It is not a creator upload system.

Catalog records use provider-neutral asset keys for video, poster, and captions. A resolver may produce delivery URLs. Development uses explicit local/test fixtures. Production owned or licensed object storage and CDN delivery is deferred, as are credentials and network ingestion. Arbitrary external hotlinks are not considered production-ready.

## Migration compatibility

Keep the existing tables and identities. A later migration may add normalized metadata, but it must retain `video_id`, current read routes, legacy caption meaning, and source references. Existing `media_url` needs a compatibility adapter to a provider-neutral asset reference. Backfill must not invent rights or review facts; the flower fixture remains development-only until genuinely reviewed.

## Staged implementation

1. After rights-cleared packages exist, add only the catalog fixture and provider-neutral asset-manifest contract with fail-closed validation.
2. Add compatible persistence and deterministic cursor API behavior.
3. Add exact-record navigation and return-state contracts.
4. Build the playable web feed and close mobile parity gaps.
5. Add the private reviewed editorial workflow.
6. Complete browser/device accessibility, failure, navigation, sharing, pagination, and bounded performance acceptance.

Public uploads, recording, creator accounts, messages, likes, follows, public counts, recommendations, profiling, notifications, ads, monetization, broad moderation, production credentials, network ingestion, and external publishing remain deferred.
