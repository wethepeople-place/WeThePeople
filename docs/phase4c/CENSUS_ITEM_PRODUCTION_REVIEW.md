# Census item production review

Date: 2026-08-04

Scope: `housing-rent-why-rents-move` / YouTube `-Zfh6IKiJ4s`

Decision: **approved in the source registry for official embedding; production remains disabled and canonical link-out remains the runtime fallback**

The user separately authorized the registry-approval-only decision. This review
approves the Census source contract for `official_embed` and `link_out`, but it
does not enable production playback, change runtime behavior, authorize
downloads, add credentials or ingestion, or authorize publication.

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

## Registry approval

The source registry now lists Census as `approved` for `official_embed` and
`link_out`. It records the exact verified channel, YouTube embed terms and
review date, privacy review, per-item transcript requirement, text-card poster
fallback, evidence expiry, and takedown path. The other four researched sources
remain candidate link-outs.

## Reconsideration boundary

Registry approval is complete. Production playback remains a separate authority
boundary. `production_media_enabled` and runtime authorization remain `false`,
all operational authorization flags remain false, and canonical link-out remains
the only production-safe runtime behavior until the user separately authorizes
and reviews production enablement.
