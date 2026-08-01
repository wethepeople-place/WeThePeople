# Phase 4: read-only Watch slice

This checkpoint adds one curated Housing & Rent Watch item without importing
the audited reference application's Firebase architecture or social schema.
The reference audit and keep/replace/defer decision were recorded in the
parent project's `wethepeopleplace-memorycodex.md` before this branch existed.

## Fixed contract

- Exactly one network-free curated fixture: `housing-rent-why-rents-move`.
- Exactly one issue relationship: `housing-rent`.
- Exactly one related bill: `hr1-119`.
- Public read-only endpoints: `GET /videos` and `GET /videos/{video_id}`, with
  matching `/v1` aliases.
- Stable ordering by editorial sort order, publication time, and stable ID.
- Every returned item has an HTTPS evidence source, publisher, and retrieval
  timestamp. Incomplete provenance fails closed.
- Caption and transcript are first-class fields. A captions-file URL is
  optional because the first item supplies an inline transcript.

## Loading the fixture

First load a complete, reviewed Housing & Rent fixture so the issue and bill
exist. Then run:

```bash
python -m jobs.load_watch_fixture data/watch_housing_rent.json
```

The loader performs no network calls, reads no credentials, validates the
entire payload before writes, and is idempotent. It does not depend on the
deferred HUD token.

## Expo checkpoint

The new Watch tab uses Expo's supported video component and the existing API
client/navigation foundation. It provides vertical paging, majority-visible
single-item activation, app/tab focus pause, reduced-motion opt-in playback,
captions/transcript visibility, labeled controls, and explicit loading, empty,
error, and unavailable-source experiences. Evidence, issue, and bill actions
remain read-only links.

## Explicit exclusions

No Firebase, Sanity, upload, camera, creator publishing, likes, comments,
follows, bookmarks, messaging, ranking, recommendations, analytics, storage,
CDN, or moderation architecture is introduced in this slice.
