# Phase 4C approved-source registry contract

The approved-source registry is a non-operational allowlist contract for the hybrid Watch delivery policy. The checked-in registry approves the Census Bureau for `official_embed` and `link_out` based on the exact verified channel, current platform terms, privacy review, and a per-item transcript requirement. Government Accountability Office, National Archives, Library of Congress, and Congressional Budget Office remain candidates restricted to `link_out`. Registry approval does not activate production media or runtime playback.

Each source record identifies the publisher, official HTTPS domains and channels, canonical source page, allowed delivery modes, supporting evidence, privacy posture, poster policy, accessibility requirements, review and expiry dates, and takedown path. A source that is not `approved` may use only `link_out`. Suspension or expired evidence also falls back to link-out.

Conditional evidence is required by delivery mode:

- Official embeds require the official channel reference, embed terms and review date, and privacy review.
- Licensed hosting requires an owned, licensed, public-domain, or publisher-agreement basis, evidence reference, allowed uses, and rights review date.
- Publisher feeds additionally require a publisher warranty, stable feed identity, takedown contact, and audit retention.
- Link-out requires only a canonical page on an official domain and does not claim media reuse rights.

Playable sources require captions or a transcript. Posters require an owned, licensed, publisher-supplied, or embed-rendered basis; otherwise Watch uses a text card. Validation is read-only and network-free. It never fetches terms, probes channels, downloads assets, stores credentials, or publishes media.

## Pilot research result

All five publishers have an official agency page identifying a video collection or YouTube channel. YouTube provides an official embedding mechanism and privacy-enhanced mode, but its embedded player still shares basic data with YouTube and its policies impose player, autoplay, branding, visibility, and referrer requirements. That platform-level permission does not by itself prove publisher-specific poster rights or per-item caption coverage.

Census has the strongest source-level reuse evidence: its multimedia policy permits Census media assets in news media and public-information products, with attribution and noncommercial, no-endorsement, and no-resale restrictions. Its privacy policy also warns that embedded third-party services may collect visitor information. GAO states that its video files have closed captions and transcripts. NARA states that only some transcripts are currently available. The Library of Congress warns that third-party platforms collect information outside its control and that collection rights vary. CBO identifies its official channel but the bounded review did not locate equivalent source-level embed, poster, privacy, or catalog-wide caption terms.

The exact Census pilot passed the separate item-level accessibility/privacy review and the user authorized both registry approval and a later exact-item production implementation. Its approval expires on 2026-11-04 unless the evidence is reviewed again. The other four sources remain candidate link-outs because their gaps have not been resolved. Source approval alone never activates playback: the separate production allowlist, server kill switch, exact identity match, and unexpired evidence are also required. Unknown, suspended, or expired evidence continues to fail closed.
