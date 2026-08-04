# Census item production review

Date: 2026-08-04

Scope: `housing-rent-why-rents-move` / YouTube `-Zfh6IKiJ4s`

Decision: **not eligible for registry approval; retain canonical link-out**

This review is decision-only. It does not approve the Census source, change the
source registry, enable production playback, authorize downloads, or authorize
publication.

## Evidence that passed

- The live Census page embeds the exact YouTube video ID recorded by the
  development fixture and links an official transcript.
- The live YouTube page identifies the verified U.S. Census Bureau channel.
- Current YouTube documentation permits standard embeds, documents
  privacy-enhanced mode, requires an HTTP referrer, preserves player controls
  and branding, and prohibits overlays over the player. The development adapter
  already follows those technical boundaries.
- The text-card fallback avoids unreviewed poster or thumbnail reuse.

## Blocking findings

1. The live YouTube player reports subtitles/closed captions unavailable.
2. The checked-in Watch `transcript` is an editorial summary, not the official
   full Census transcript. It cannot satisfy the item-level transcript gate.
3. The consent notice describes third-party data sharing but does not link
   directly to the Google or YouTube privacy policy, which the Phase 4C
   compatibility contract requires.
4. The approved-source registry still correctly lists Census as `candidate`
   with `link_out` as its only allowed delivery mode.

## Reconsideration boundary

Reconsideration requires accurate integration or clearly labeled linking of the
official full transcript, a direct privacy-policy link in the consent notice,
a repeated item-level accessibility/privacy review, and separate user authority
before any registry approval or production playback. Until all four occur, the
only production-safe delivery is canonical link-out.
