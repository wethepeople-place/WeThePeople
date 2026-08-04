# Census item production review

Date: 2026-08-04

Scope: `housing-rent-why-rents-move` / YouTube `-Zfh6IKiJ4s`

Decision: **exact pilot item authorized for production playback behind an explicit server kill switch and item allowlist**

After separately authorizing the registry decision, the user authorized
production playback for this exact item only. The implementation does not
authorize downloads, add credentials or ingestion, authorize mobile inline
embedding, deploy the kill switch, or authorize publication.

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

Registry approval and exact-item production implementation are complete.
Production delivery still requires the server-side kill switch, exact allowlist,
matching source and fixture identity, and unexpired evidence. Canonical link-out
remains the failure fallback. Deployment and publication remain separate
authority boundaries.
