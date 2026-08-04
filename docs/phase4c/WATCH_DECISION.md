# Phase 4C hybrid civic-video delivery decision

## Outcome

Phase 4C adopts a hybrid delivery model designed to scale beyond item-by-item clearance. Official embeds are the default. Locally hosted media is allowed only when reuse rights are machine-verifiable or covered by a publisher agreement. Approved publisher feeds can scale either embeds or licensed hosting. When rights or platform terms are unclear, the product fails closed to a link-out card at the official source.

This policy does not enable production media, network downloads, ingestion, credentials, or publishing. The existing development Watch fixture remains clearly labeled and cannot satisfy production acceptance.

## Delivery modes

Every catalog record declares one delivery mode:

1. `official_embed` — playback remains with the official publisher or its authorized channel. Embed terms must permit embedding; no video download or redistribution is inferred.
2. `licensed_hosted` — WeThePeople.place may store and deliver the media only with owned, licensed, public-domain, or publisher-agreement evidence.
3. `publisher_feed_embed` — an approved publisher supplies stable records and authorized embed references under source-level terms.
4. `publisher_feed_hosted` — an approved publisher supplies media under a source-level license or agreement that permits storage and delivery.
5. `link_out` — the catalog provides civic context and opens the canonical official page. It never claims media reuse rights.

The scalable clearance unit is a source, channel, feed, collection, license, or publisher agreement—not a separate outreach request for every video. Item-level review is reserved for exceptions, disputed metadata, or content containing unclear third-party components.

## Fail-closed rules

Official embeds require an official publisher or channel, terms permitting embedding, a canonical source URL, no downloading or redistribution, and a privacy review. Platform thumbnails are not treated as reusable posters merely because they are visible. Use only owned, licensed, publisher-supplied, or embed-rendered poster assets; otherwise render a text card.

Local hosting requires a machine-verifiable rights basis of `owned`, `licensed`, `public_domain`, or `publisher_agreement`, plus its evidence reference and allowed uses. General government publication does not by itself prove that every component is redistributable.

Publisher feeds require an approved publisher, rights warranty, stable source identity, license or embed terms, captions or transcript, a takedown contact, and an audit trail. Automated validation fails closed. Unclear rights always fall back to link-out.

If an embed or linked source disappears, Watch preserves the transcript when permitted, official evidence, issue, bills, discussion, and provenance. Editorial narration and official evidence remain separately labeled.

## Catalog, identity, and accessibility

The initial production catalog still requires three to five reviewed records before production acceptance, but those records may use any allowed delivery mode. Each keeps stable `video_id`, one primary issue, official evidence citations, exact bill/discussion links, provenance, and review state. Returning from a destination restores the same `video_id`.

Publication requires delivery mode and reference, rights basis appropriate to that mode, provenance, transcript or captions, a permitted poster or text-card fallback, descriptive alternative text, editorial review, accessibility review, and official evidence. Missing facts do not get invented.

## Editorial and public boundary

Ingestion remains private and reviewed, with editor, reviewer, and publisher separation of duties and immutable audit events. Public uploads, recording, creator accounts, recommendations, profiling, advertising, monetization, production credentials, and open network ingestion remain deferred.

## Next implementation slice

The next bounded slice is no longer blocked on acquiring three to five media files. It may add only the hybrid delivery policy contract, an approved-source registry schema, conditional fail-closed validation, focused policy tests, and documentation. Runtime routes, UI, downloads, external publishing, production credentials, and production media enablement remain forbidden until separately authorized and reviewed.
