# Phase 5: Discuss schema foundation

This checkpoint defines the normalized records required by the Discuss product
layer before public or authenticated API behavior is added.

## Included

- root posts and nested replies using canonical `users` identities;
- civic attachments with real foreign keys to videos, issues, bills,
  politicians, citizen solutions, and normalized source documents;
- reactions, follows, and bookmarks with duplicate-edge protection;
- immutable edit-history records;
- private reports and blocks with no public serializer relationships;
- explicit post/reply moderation states: `published`, `pending`, `hidden`, and
  `removed`;
- length, target-type, reaction-value, self-follow/self-block, one-target, and
  uniqueness constraints enforced in the database;
- an Alembic migration chained from `phase4_watch_001`.

## Boundaries

The schema contains no Firebase identifiers, private messages, uploads, media
storage, notification state, recommendation/ranking data, or public moderation
records. SQLite supports local tests only; production social activity still
requires a validated PostgreSQL deployment.

The next narrow step is a curated Housing & Rent thread fixture plus public
paginated feed/detail APIs and authenticated, rate-limited reply/report/block
routes. UI work begins only after those contracts pass focused tests.

## Discuss API checkpoint

The network-free fixture loader now creates exactly one editorial Housing &
Rent thread and four typed attachments: the Watch video, issue, bill, and
Congress.gov source. Public feed and detail routes expose only `published`
content, stable chronological pagination, and complete source provenance.

Authenticated writes are limited to replies, reports, and blocks. Each uses
the canonical user identity and a persistent per-user/IP rate-limit key.
Reports and block relationships remain private; an authenticated feed filters
authors the current user has blocked. Root-post creation, editing, reactions,
follows, bookmarks, ranking, and all Expo UI remain deferred.

## Expo Discuss shell checkpoint

The Expo app now has a Discuss tab with public feed and thread-detail states,
typed API calls, evidence linking, and a Watch-to-Discuss control. Signed-in
users can reply, privately report a post, or block its author; signed-out users
are routed through the existing login boundary. Loading, empty, error, retry,
keyboard, and accessibility-label states are explicit.

Root-post creation, reactions, follows, bookmarks, ranking, broad moderation
tooling, and the HUD token remain deferred.

## Native media upload safety gate

Native photo and video upload must remain unavailable until the complete
publishing pipeline is approved and implemented. A browser file picker by
itself is not a safe release. The minimum launch gate includes:

- private object storage with short-lived signed upload credentials;
- allowlisted file signatures, size and duration limits, and per-user rate limits;
- malware scanning before any processing or reviewer access;
- image metadata, including location data, removal;
- server-side image normalization and video transcoding into safe playback formats;
- generated thumbnails plus required image alt text and video captions;
- pending moderation before public access, with reviewer audit records;
- deletion, retention, appeal, reporting, and account-lifecycle behavior;
- storage, bandwidth, processing-cost, and abuse monitoring; and
- documented recovery behavior for failed, interrupted, and duplicate uploads.

The first bounded release should allow one image per post. Short video should
follow only after the transcoding, caption, moderation, retention, and cost
controls pass security and accessibility review.
