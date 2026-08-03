# Phase 4C Watch and YouTube embed compatibility audit

## Decision

The existing Watch interaction model is a useful foundation, but neither current player can safely accept YouTube URLs. Web uses a native `<video>` element and mobile uses Expo Video; YouTube requires its official embedded player. No embed adapter is authorized or added by this audit.

## Keep

Keep stable `video_id` and exact URLs, the 60% visibility threshold, one-active behavior, inactive and background pausing, reduced-motion gates, manual playback, transcripts, unavailable-media context, civic record navigation, and loading/empty/error states. These align well with YouTube's visibility and one-autoplay-player requirements.

## Repair before a web adapter

Use a discriminated delivery mode and provider reference. Before consent, render an authorized poster or text card and canonical source link without loading YouTube. A future development-only adapter should load an official privacy-enhanced iframe only after a clear user action, preserve YouTube branding and controls, use `strict-origin-when-cross-origin`, and never cover the player or controls with Watch overlays. Transcript, civic context, and actions must sit outside the iframe bounds.

Do not autoplay before consent. If visible autoplay is later enabled after consent, it must begin muted, only when more than half visible, and never allow more than one player to autoplay. Inactive embeds should not preload. The player must be at least 200 by 200 pixels, remain keyboard reachable, expose a clear privacy notice, and fall back to the transcript, evidence, text card, and canonical official link when unavailable.

The existing mobile “Captions” toggle displays editorial transcript text, not a media caption track, and must be relabeled. Per-item playback still requires either verified captions or an accessible transcript.

## Mobile decision

Expo Video cannot serve as the YouTube adapter. No React Native WebView dependency or embed lifecycle exists. Mobile therefore remains canonical link-out for embed sources. Inline mobile playback is deferred until an OS WebView design proves referrer identity, consent and privacy behavior, official controls and branding, one-active lifecycle, failure handling, and device accessibility.

## Credentials and deferred work

A static official iframe does not require an API key, but YouTube Data API use, channel ingestion, high-volume API access, or additional credentials require a new review. Defer the Data API, credentials, playlist/channel ingestion, automatic thumbnail fetching or caching, custom player chrome, overlays, background playback, inactive embed preloading, source approval, and production playback.

## Recommended next slice

If separately authorized, the smallest safe implementation is a development-only web adapter for one approved test source record: click-to-load consent, privacy-enhanced official iframe, no autoplay before consent, preserved controls and branding, transcript and actions outside the player, and canonical link-out fallback. Mobile and production remain link-out only.
