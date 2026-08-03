# Phase 4C approved-source registry contract

The approved-source registry is a non-operational allowlist contract for the hybrid Watch delivery policy. The checked-in registry starts empty. An empty registry is intentional: it activates no production media and makes no publisher, channel, license, privacy, poster, or accessibility claims.

Each future source record identifies the publisher, official HTTPS domains and channels, canonical source page, allowed delivery modes, supporting evidence, privacy posture, poster policy, accessibility requirements, review and expiry dates, and takedown path. A source that is not `approved` may use only `link_out`. Suspension or expired evidence also falls back to link-out.

Conditional evidence is required by delivery mode:

- Official embeds require the official channel reference, embed terms and review date, and privacy review.
- Licensed hosting requires an owned, licensed, public-domain, or publisher-agreement basis, evidence reference, allowed uses, and rights review date.
- Publisher feeds additionally require a publisher warranty, stable feed identity, takedown contact, and audit retention.
- Link-out requires only a canonical page on an official domain and does not claim media reuse rights.

Playable sources require captions or a transcript. Posters require an owned, licensed, publisher-supplied, or embed-rendered basis; otherwise Watch uses a text card. Validation is read-only and network-free. It never fetches terms, probes channels, downloads assets, stores credentials, or publishes media.
