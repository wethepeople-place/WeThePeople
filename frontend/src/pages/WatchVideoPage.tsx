import { useEffect, useState } from 'react';
import { ExternalLink } from 'lucide-react';
import { useParams } from 'react-router-dom';

import { getApiBaseUrl } from '../api/client';
import type { VideoSharePreview } from '../api/types';
import ShareButton from '../components/ShareButton';

function setMeta(property: string, content: string) {
  let element = document.head.querySelector<HTMLMetaElement>(`meta[property="${property}"]`);
  if (!element) {
    element = document.createElement('meta');
    element.setAttribute('property', property);
    document.head.appendChild(element);
  }
  element.content = content;
}

export default function WatchVideoPage() {
  const { videoId = '' } = useParams();
  const [preview, setPreview] = useState<VideoSharePreview | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${getApiBaseUrl()}/videos/${encodeURIComponent(videoId)}/share`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error(response.status === 404 ? 'Video not found' : 'Preview unavailable');
        return response.json() as Promise<VideoSharePreview>;
      })
      .then((data) => {
        setPreview(data);
        document.title = data.title;
        setMeta('og:type', 'video.other');
        setMeta('og:title', data.title);
        setMeta('og:description', data.description);
        setMeta('og:url', data.canonical_url);
        if (data.image_url) setMeta('og:image', data.image_url);
        let canonical = document.head.querySelector<HTMLLinkElement>('link[rel="canonical"]');
        if (!canonical) {
          canonical = document.createElement('link');
          canonical.rel = 'canonical';
          document.head.appendChild(canonical);
        }
        canonical.href = data.canonical_url;
      })
      .catch((reason) => { if (reason.name !== 'AbortError') setError(reason.message); });
    return () => controller.abort();
  }, [videoId]);

  if (error) return <main className="min-h-screen bg-bg px-6 py-20 text-text-1"><div className="mx-auto max-w-2xl rounded-card border border-border bg-surface p-8"><h1 className="font-display text-3xl">Video unavailable</h1><p className="mt-3 text-text-2">{error}. The link may be invalid or the preview may be temporarily unavailable.</p></div></main>;
  if (!preview) return <main className="min-h-screen bg-bg p-20 text-center text-text-2">Loading civic video preview…</main>;

  return <main className="min-h-screen bg-bg px-5 py-14 text-text-1"><article className="mx-auto max-w-3xl rounded-card border border-border bg-surface p-7 sm:p-10"><p className="text-xs font-bold uppercase tracking-[0.18em] text-accent-text">Watch · Housing &amp; Rent</p><h1 className="mt-4 font-display text-3xl sm:text-5xl">{preview.title.replace(' | WeThePeople.place', '')}</h1><p className="mt-5 text-lg leading-8 text-text-2">{preview.description}</p><div className="mt-7 flex flex-wrap gap-3"><ShareButton url={preview.canonical_url} title={preview.title} text={preview.description} /></div><p className="mt-8 text-sm text-text-2">Official source: <a className="text-accent-text hover:underline" href={preview.source.url} target="_blank" rel="noreferrer">{preview.source.publisher} <ExternalLink className="inline h-4 w-4" /></a></p></article></main>;
}
