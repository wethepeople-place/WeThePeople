import { useEffect, useState } from 'react';
import { Bookmark, ExternalLink, Heart, MessageCircle, X } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';

import { getApiBaseUrl } from '../api/client';
import type { IssueVideo } from '../api/issues';
import { useAuth } from '../contexts/AuthContext';
import { getOfficialEmbedUrl, getValidatedProvider } from '../features/watch/providers';
import ShareButton from './ShareButton';
import VideoCommentsPanel from './VideoCommentsPanel';

type Props = { video: IssueVideo | null; returnPath: string; onClose: () => void; onChange: (video: IssueVideo) => void };

function posterUrl(video: IssueVideo) {
  const value = video.delivery?.poster_url;
  return value?.startsWith('/') ? `${getApiBaseUrl()}${value}` : value;
}

export default function IssueVideoDialog({ video, returnPath, onClose, onChange }: Props) {
  const { isAuthenticated, authedFetch } = useAuth();
  const navigate = useNavigate();
  const [busy, setBusy] = useState('');
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (!video) return;
    const before = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const close = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose(); };
    window.addEventListener('keydown', close);
    return () => { document.body.style.overflow = before; window.removeEventListener('keydown', close); };
  }, [onClose, video]);

  if (!video) return null;

  const toggle = async (kind: 'like' | 'save') => {
    if (!isAuthenticated) { navigate(`/login?next=${encodeURIComponent(returnPath)}`); return; }
    setBusy(kind); setMessage('');
    try {
      const active = kind === 'like' ? !video.liked : !video.saved;
      const response = await authedFetch(`${getApiBaseUrl()}/videos/${encodeURIComponent(video.video_id)}/${kind}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ active }) });
      if (!response.ok) throw new Error(`Could not update ${kind}.`);
      const state = await response.json();
      onChange({ ...video, ...state });
      setMessage(kind === 'like' ? (state.liked ? 'Video liked.' : 'Like removed.') : (state.saved ? 'Video saved.' : 'Video removed from saved.'));
    } catch (reason) { setMessage(reason instanceof Error ? reason.message : 'Action could not be saved.'); }
    finally { setBusy(''); }
  };

  const rawDelivery = video.delivery;
  const normalizedDelivery = rawDelivery ? {
    mode: rawDelivery.mode || 'link_out', provider: rawDelivery.provider,
    provider_video_id: rawDelivery.provider_video_id, canonical_url: rawDelivery.canonical_url || video.source?.url || '',
    source_label: rawDelivery.source_label || video.creator_label, poster_url: rawDelivery.poster_url,
    development_only: Boolean(rawDelivery.development_only),
  } : null;
  const provider = normalizedDelivery ? getValidatedProvider(normalizedDelivery) : null;
  const embedUrl = provider && normalizedDelivery?.mode === 'official_embed' ? getOfficialEmbedUrl(normalizedDelivery) : null;
  const canonicalUrl = normalizedDelivery?.canonical_url || video.source?.url || '';

  return <div className="fixed inset-0 z-[100] bg-black/75 p-0 md:p-5" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section role="dialog" aria-modal="true" aria-labelledby="issue-video-title" className="mx-auto grid h-full max-w-7xl overflow-hidden bg-[#070b14] text-white shadow-2xl md:h-[calc(100vh-2.5rem)] md:grid-cols-[minmax(0,1fr)_minmax(340px,420px)] md:rounded-3xl md:border md:border-white/15">
      <div className="flex min-h-0 flex-col">
        <header className="flex items-center justify-between gap-4 border-b border-white/10 px-4 py-3 sm:px-6">
          <div className="min-w-0"><p className="text-[11px] font-black uppercase tracking-[.14em] text-amber-300">Watch without leaving this issue</p><h2 id="issue-video-title" className="truncate text-base font-black sm:text-lg">{video.caption}</h2></div>
          <button autoFocus type="button" onClick={onClose} className="grid min-h-11 min-w-11 shrink-0 place-content-center rounded-full bg-white/10 outline-none hover:bg-white/15 focus-visible:ring-4 focus-visible:ring-amber-300/70" aria-label="Close video"><X className="h-5 w-5" /></button>
        </header>
        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
          <div className="relative grid min-h-[250px] flex-1 place-content-center overflow-hidden bg-black sm:min-h-[360px]">
            {embedUrl ? <iframe className="absolute inset-0 h-full w-full" src={embedUrl} title={video.caption} referrerPolicy="strict-origin-when-cross-origin" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowFullScreen />
              : normalizedDelivery?.mode === 'hosted_video' && video.media_url ? <video className="absolute inset-0 h-full w-full object-contain" src={video.media_url} controls playsInline />
                : <div className="absolute inset-0 flex flex-col items-center justify-center p-8 text-center">{posterUrl(video) && <img src={posterUrl(video)!} alt="" className="absolute inset-0 h-full w-full object-cover opacity-35" />}<div className="absolute inset-0 bg-black/50" /><div className="relative"><p className="font-bold text-slate-200">Playback opens at the original source.</p>{canonicalUrl && <a className="mt-4 inline-flex min-h-11 items-center gap-2 rounded-full bg-white px-5 font-black text-slate-950" href={canonicalUrl} target="_blank" rel="noreferrer">Open video <ExternalLink className="h-4 w-4" /></a>}</div></div>}
          </div>
          <div className="p-4 sm:p-6"><p className="text-sm font-bold uppercase tracking-wider text-amber-300">{video.creator_label}</p><h3 className="mt-2 text-xl font-black sm:text-2xl">{video.caption}</h3>
            <div className="mt-5 flex flex-wrap gap-2">
              <button type="button" disabled={busy === 'like'} aria-pressed={Boolean(video.liked)} onClick={() => void toggle('like')} className="inline-flex min-h-11 items-center gap-2 rounded-full bg-white/10 px-4 font-bold"><Heart className={`h-5 w-5 ${video.liked ? 'fill-rose-500 text-rose-500' : ''}`} />{video.like_count || 0}</button>
              <button type="button" disabled={busy === 'save'} aria-pressed={Boolean(video.saved)} onClick={() => void toggle('save')} className="inline-flex min-h-11 items-center gap-2 rounded-full bg-white/10 px-4 font-bold"><Bookmark className={`h-5 w-5 ${video.saved ? 'fill-white' : ''}`} />Save</button>
              <span className="inline-flex min-h-11 items-center gap-2 rounded-full bg-white/10 px-4 font-bold"><MessageCircle className="h-5 w-5" />{video.discussion_count || 0}</span>
              <ShareButton url={`${window.location.origin}/videos/${video.video_id}`} title={video.caption} text={video.caption} />
            </div>
            <p className="sr-only" role="status" aria-live="polite">{message}</p>
            <Link className="mt-5 inline-block text-sm font-bold text-amber-300 underline" to={`/videos/${video.video_id}`}>Open full video page</Link>
          </div>
        </div>
      </div>
      <div className="min-h-0 border-t border-white/10 md:border-l md:border-t-0"><VideoCommentsPanel embedded videoId={video.video_id} videoCaption={video.caption} open onClose={onClose} /></div>
    </section>
  </div>;
}
