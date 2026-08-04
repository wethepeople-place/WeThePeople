# Census item production review

Date: 2026-08-04

Scope: `housing-rent-why-rents-move` / YouTube `-Zfh6IKiJ4s`

Decision: **eligible for a separate registry-approval review; retain canonical link-out until separately authorized**

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

## Remediation completed

1. The live YouTube player still reports subtitles/closed captions unavailable;
   the record now exposes the official full Census transcript as its accessible
   alternative without copying or downloading it.
2. The checked-in editorial text is now labeled `Overview`, not `Transcript`.
3. The consent notice now links directly to Google's privacy policy before the
   player can load.

## Remaining blocker

The approved-source registry still correctly lists Census as `candidate` with
`link_out` as its only allowed delivery mode. This remediation does not grant
authority to change that state.

## Reconsideration boundary

The item is eligible for a separate registry-approval review because the
item-level accessibility and privacy gates now pass. Actual registry approval
and production playback still require separate user authority. Until that
authority and registry mutation occur, the only production-safe delivery is
canonical link-out.
