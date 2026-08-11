import { useState } from 'react';
import type { DiscussionVideoLink } from '../api/civic';
import { getOfficialEmbedUrl, getProviderPrivacyUrl } from '../features/watch/providers';

export default function DiscussionVideoEmbed({ video, title }: { video: DiscussionVideoLink; title: string }) {
  const [consented, setConsented] = useState(false);
  const embedUrl = getOfficialEmbedUrl(video);
  if (!embedUrl) return <a className="text-accent-text underline" href={video.canonical_url} target="_blank" rel="noreferrer">Watch on YouTube</a>;
  return <div className="mt-5 overflow-hidden rounded-card border border-border bg-[#111827] text-white"><div className="relative aspect-video">
    {consented ? <iframe className="absolute inset-0 h-full w-full" src={embedUrl} title={title} referrerPolicy="strict-origin-when-cross-origin" allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowFullScreen /> : <div className="absolute inset-0 grid place-content-center p-6 text-center">
      <p className="font-semibold">Video shared from YouTube</p>
      <p className="mt-2 text-sm text-slate-300">The player stays off until you choose to load it. YouTube will then receive request and playback data under its <a className="text-amber-300 underline" href={getProviderPrivacyUrl('youtube')} target="_blank" rel="noreferrer">privacy policy</a>.</p>
      <button className="mx-auto mt-4 rounded-full bg-white px-5 py-3 font-bold text-slate-950 outline-none focus-visible:ring-4 focus-visible:ring-amber-300/70" onClick={() => setConsented(true)}>Load YouTube video</button>
      <a className="mt-3 text-sm text-amber-300 underline" href={video.canonical_url} target="_blank" rel="noreferrer">Watch on YouTube instead</a>
    </div>}
  </div></div>;
}
