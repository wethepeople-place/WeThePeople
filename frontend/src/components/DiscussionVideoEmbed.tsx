import { useState } from 'react';
import { Play } from 'lucide-react';
import type { DiscussionVideoLink } from '../api/civic';
import { getOfficialEmbedUrl, getProviderLabel, getProviderPrivacyUrl } from '../features/watch/providers';

export default function DiscussionVideoEmbed({ video, title }: { video: DiscussionVideoLink; title: string }) {
  const [consented, setConsented] = useState(false);
  const embedUrl = getOfficialEmbedUrl(video);
  const providerLabel = video.provider === 'instagram' ? 'Instagram' : getProviderLabel(video.provider);
  if (!embedUrl) return <a className="mt-4 inline-flex min-h-11 items-center text-accent-text underline" href={video.canonical_url} target="_blank" rel="noopener noreferrer">Open on {providerLabel}</a>;
  return <div className="mt-5 overflow-hidden rounded-card border border-border bg-[#111827] text-white"><div className="relative aspect-video">
    {consented ? <iframe className="absolute inset-0 h-full w-full" src={embedUrl} title={title} referrerPolicy="strict-origin-when-cross-origin" allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowFullScreen /> : <div className="absolute inset-0 grid place-content-center bg-gradient-to-b from-slate-800 to-slate-950 p-6 text-center">
      <p className="font-semibold">Video shared from {providerLabel}</p>
      <button aria-label={`Play video from ${providerLabel}`} className="mx-auto mt-4 grid h-16 w-16 place-content-center rounded-full bg-white text-slate-950 outline-none transition hover:scale-105 focus-visible:ring-4 focus-visible:ring-amber-300/70" onClick={() => setConsented(true)}><Play className="ml-1 h-7 w-7 fill-current" aria-hidden="true" /></button>
      <p className="mt-3 text-sm text-slate-300">Playing connects to {providerLabel}. <a className="text-amber-300 underline" href={getProviderPrivacyUrl(video.provider as 'youtube' | 'tiktok' | 'facebook')} target="_blank" rel="noreferrer">Privacy details</a></p>
      <a className="mt-3 text-sm text-amber-300 underline" href={video.canonical_url} target="_blank" rel="noopener noreferrer">Open on {providerLabel} instead</a>
    </div>}
  </div></div>;
}
