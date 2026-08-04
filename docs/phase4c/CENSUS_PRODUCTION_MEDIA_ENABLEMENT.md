# Census exact-item production media enablement

Date: 2026-08-04

The user authorized production playback for exactly one approved pilot record: `housing-rent-why-rents-move`, using U.S. Census Bureau YouTube video `-Zfh6IKiJ4s`. This is an implementation authorization, not deployment or publication authorization.

Playback requires every gate below:

- `WTP_ENV=production`;
- `WTP_ENABLE_PRODUCTION_WATCH_EMBED=true` on the API server;
- an exact match in `config/watch_phase4c_production_media_allowlist.json`;
- an approved Census source registry entry allowing `official_embed`;
- matching provider, video, canonical URL, and official transcript metadata;
- evidence that has not reached its 2026-11-04 expiry.

If any gate fails, the API omits production delivery metadata and Watch cannot create the embed. The allowlist contains one item only. It explicitly requires web consent, privacy-enhanced YouTube hosting, canonical link-out fallback, official transcript access, and mobile link-out. Credentials, downloads, ingestion, mobile inline embedding, and publication remain unauthorized.

The web player still starts with zero iframe requests. Only the user's `Load official video` action creates the `youtube-nocookie.com` iframe. The canonical source link, Google Privacy Policy link, official Census transcript, text-card fallback, official player controls, strict referrer policy, and active-card unload behavior remain intact.

The checked-in environment example keeps the production kill switch `false`. Enabling it in a deployed environment or publishing the change requires separate user authority.
