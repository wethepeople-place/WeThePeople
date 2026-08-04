# Phase 4C development-only web embed adapter

The user approved one bounded runtime experiment after the embed compatibility audit. The web Watch feed now contains an explicit adapter for the development fixture `housing-rent-why-rents-move`, mapped to the verified U.S. Census Bureau YouTube video `-Zfh6IKiJ4s`.

The adapter is disabled by default and exists only when both conditions are true:

- Vite is running in development mode; and
- `VITE_ENABLE_DEVELOPMENT_WATCH_EMBED=true` is explicitly set for that local process.

Production builds compile the adapter mapping to an empty registry. The API, database, mobile app, production source registry, and production media state are unchanged.

Before consent, Watch renders a text card, privacy notice, transcript, civic links, and canonical YouTube link. It makes no iframe request. After the user selects **Load official video**, Watch creates one official privacy-enhanced iframe using `youtube-nocookie.com`, `autoplay=0`, visible YouTube controls and branding, and `strict-origin-when-cross-origin`. No Watch content overlays the iframe. Transcript and civic actions remain outside the player.

The iframe exists only while its card is active. Moving to another card removes it; returning restores one iframe after the prior consent. The adapter downloads or caches no media or thumbnail, uses no YouTube Data API or credential, and does not approve Census—or any other source—for production playback. Mobile remains unchanged and link-out-only for future embed sources.
