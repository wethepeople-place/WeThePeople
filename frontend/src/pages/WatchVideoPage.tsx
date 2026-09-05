import { useCallback, useEffect, useRef, useState } from 'react';
import { Bookmark, ChevronDown, ExternalLink, Heart, Image as ImageIcon, Link2, MessageCircle, Pause, Play, SquarePen, Video as VideoIcon, Volume2, VolumeX } from 'lucide-react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';

import { getApiBaseUrl } from '../api/client';
import ShareButton from '../components/ShareButton';
import VideoCommentsPanel from '../components/VideoCommentsPanel';
import { useAuth } from '../contexts/AuthContext';
import { getOfficialEmbedUrl, getProviderLabel, getProviderPrivacyUrl, getValidatedProvider } from '../features/watch/providers';

type Video = {
  video_id: string; content_origin?: 'reviewed' | 'community'; creator_label: string; caption: string; transcript: string | null;
  media_url: string; published_at: string;
  delivery: Delivery | null;
  accessibility: Accessibility | null;
  source: { url: string; publisher: string }; issue: { slug: string; title: string };
  bills: Array<{ bill_id: string; title: string | null }>;
  discussion_post_id: number | null;
  like_count: number; discussion_count: number; liked: boolean; saved: boolean;
};
type Feed = { videos: Video[]; next_cursor: string | null; has_more: boolean };

type AgendaFallback = {
  kind: 'agenda'; key: string; slug: string; title: string; summary: string | null;
  evidenceNote: string | null; billCount: number;
};
type BillFallback = {
  kind: 'bill'; key: string; billId: string; title: string; latestAction: string | null;
  latestActionDate: string | null;
};
type CivicFallback = AgendaFallback | BillFallback;

type Delivery = {
  mode: 'official_embed' | 'hosted_video' | 'link_out'; provider: string | null;
  provider_video_id: string | null; canonical_url: string; source_label: string | null;
  poster_url?: string | null;
  development_only: boolean;
};

type Accessibility = {
  text_kind: 'overview' | 'transcript'; official_transcript_url: string;
  official_transcript_label: string; overview_points?: string[]; development_only: boolean;
};

const DEVELOPMENT_EMBED_AUTHORIZED = import.meta.env.DEV && import.meta.env.VITE_ENABLE_DEVELOPMENT_WATCH_EMBED === 'true';

function WatchQuickComposer() {
  const composeUrl = '/discuss?compose=1#composer';
  const lockedClass = 'inline-flex min-h-11 items-center gap-2 rounded-full px-3 text-sm font-bold text-slate-500 opacity-80';
  return <aside className="mx-auto w-[calc(100%-2rem)] max-w-3xl rounded-2xl border border-white/15 bg-slate-900/95 p-3 text-white shadow-2xl shadow-black/40 backdrop-blur sm:flex sm:items-center sm:gap-3" aria-label="Create a civic post">
    <Link className="flex min-h-12 min-w-0 flex-1 items-center gap-3 rounded-full bg-white/10 px-4 text-left text-sm font-semibold text-slate-200 outline-none transition hover:bg-white/15 focus-visible:ring-4 focus-visible:ring-amber-300/70 sm:text-base" to={composeUrl}>
      <span className="grid h-9 w-9 shrink-0 place-content-center rounded-full bg-amber-300 text-slate-950"><SquarePen className="h-5 w-5" aria-hidden="true" /></span>
      <span className="truncate">Share a civic video, link, or thought…</span>
    </Link>
    <div className="mt-2 flex items-center justify-center gap-1 sm:mt-0" aria-label="Post options">
      <Link className="inline-flex min-h-11 items-center gap-2 rounded-full px-3 text-sm font-bold text-amber-300 outline-none hover:bg-white/10 focus-visible:ring-4 focus-visible:ring-amber-300/70" to={composeUrl}><Link2 className="h-5 w-5" aria-hidden="true" />Post link</Link>
      <button className={lockedClass} type="button" disabled aria-label="Image — coming soon" title="Image uploads are coming after safety controls are ready"><ImageIcon className="h-5 w-5" aria-hidden="true" />Image</button>
      <button className={lockedClass} type="button" disabled aria-label="Upload video — coming soon" title="Video uploads are coming after safety controls are ready"><VideoIcon className="h-5 w-5" aria-hidden="true" />Upload</button>
    </div>
  </aside>;
}

function CivicActions({ item }: { item: Video }) {
  return <div className="mt-5 min-w-0">
    <div aria-label="Explore this video" className="flex flex-wrap gap-3">
      <Link className="inline-flex min-h-12 items-center rounded-full bg-amber-300 px-5 font-bold text-slate-950 outline-none focus-visible:ring-4 focus-visible:ring-amber-300/70" to={`/issues/${item.issue.slug}`} state={{ returnToVideoId: item.video_id }}>Explore {item.issue.title}</Link>
      <Link className="inline-flex min-h-12 items-center rounded-full border border-amber-300/50 px-5 font-bold text-amber-300 outline-none focus-visible:ring-4 focus-visible:ring-amber-300/70" to={`/act?target_type=video&target_id=${encodeURIComponent(item.video_id)}`}>Take action</Link>
      <Link className="inline-flex min-h-12 items-center rounded-full border border-white/25 bg-white/10 px-5 font-bold text-white outline-none transition hover:bg-white/15 focus-visible:ring-4 focus-visible:ring-amber-300/70" to="/issues/jobs-unemployment#federal-jobs">Apply for a job</Link>
      <Link className="inline-flex min-h-12 items-center rounded-full border border-white/25 bg-white/10 px-5 font-bold text-white outline-none transition hover:bg-white/15 focus-visible:ring-4 focus-visible:ring-amber-300/70" to="/forecasts">Place your forecast</Link>
    </div>
    {(item.content_origin !== 'community' || item.bills.length > 0) && <div aria-label="Video sources" className="mt-3 flex flex-wrap gap-3 [&_a]:rounded-full [&_a]:bg-white/90 [&_a]:px-4 [&_a]:py-3 [&_a]:font-bold [&_a]:text-slate-950 [&_a]:outline-none [&_a]:focus-visible:ring-4 [&_a]:focus-visible:ring-amber-300/70">
      {item.content_origin !== 'community' && <a href={item.source.url} target="_blank" rel="noreferrer">{item.source.publisher} <ExternalLink className="inline h-4 w-4" /></a>}
      {item.bills.map((bill) => <Link key={bill.bill_id} to={`/politics/bill/${bill.bill_id}`} state={{ returnToVideoId: item.video_id }}>{bill.bill_id.toUpperCase()}</Link>)}
    </div>}
  </div>;
}

function ActionRail({ item, onChange, onComments }: { item: Video; onChange: (next: Video) => void; onComments: () => void }) {
  const { isAuthenticated, authedFetch } = useAuth();
  const navigate = useNavigate();
  const [busy, setBusy] = useState<'like' | 'save' | ''>('');
  const [message, setMessage] = useState('');
  const buttonClass = 'grid min-h-14 min-w-14 place-items-center gap-1 rounded-full bg-black/65 p-2 text-xs font-bold text-white outline-none transition focus-visible:ring-4 focus-visible:ring-amber-300/70 disabled:opacity-60';
  const signIn = () => navigate(`/login?next=${encodeURIComponent(`/videos/${item.video_id}`)}`);
  const toggle = async (kind: 'like' | 'save') => {
    if (!isAuthenticated) { signIn(); return; }
    setBusy(kind); setMessage('');
    try {
      const active = kind === 'like' ? !item.liked : !item.saved;
      const response = await authedFetch(`${getApiBaseUrl()}/videos/${encodeURIComponent(item.video_id)}/${kind}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ active }) });
      if (!response.ok) throw new Error(`Could not update ${kind}.`);
      const state = await response.json();
      onChange({ ...item, ...state });
      setMessage(kind === 'like' ? (state.liked ? 'Video liked.' : 'Like removed.') : (state.saved ? 'Video saved privately.' : 'Video removed from saved.'));
    } catch (reason) { setMessage(reason instanceof Error ? reason.message : 'Action failed.'); }
    finally { setBusy(''); }
  };
  return <aside className="absolute bottom-5 right-3 z-10 flex flex-col gap-3 sm:right-5" aria-label="Video actions">
    <button type="button" className={buttonClass} aria-label={`${item.liked ? 'Unlike' : 'Like'} video, ${item.like_count} likes`} aria-pressed={item.liked} disabled={busy === 'like'} onClick={() => void toggle('like')}><Heart className={`h-6 w-6 ${item.liked ? 'fill-rose-500 text-rose-500' : ''}`} aria-hidden="true" /><span aria-live="polite">{item.like_count}</span></button>
    <button type="button" className={buttonClass} aria-label={item.saved ? 'Remove video from private saved collection' : 'Save video privately'} aria-pressed={item.saved} disabled={busy === 'save'} onClick={() => void toggle('save')}><Bookmark className={`h-6 w-6 ${item.saved ? 'fill-amber-300 text-amber-300' : ''}`} aria-hidden="true" /><span>Save</span></button>
    <button type="button" className={buttonClass} aria-label={`Open comments for this video, ${item.discussion_count} published contributions`} onClick={onComments}><MessageCircle className="h-6 w-6" aria-hidden="true" /><span>{item.discussion_count}</span></button>
    <ShareButton rail url={`${window.location.origin}/videos/${item.video_id}`} title={item.caption} text={item.caption} />
    <span className="sr-only" role="status" aria-live="polite">{message}</span>
  </aside>;
}

function WatchStatus({ item, provider, position, total }: { item: Video; provider: string; position: number; total: number }) {
  return <div className="flex flex-wrap items-center gap-2 text-xs font-bold uppercase tracking-widest">
    <span className="rounded-full bg-white/10 px-3 py-1.5 text-white">{provider}</span>
    <span className="rounded-full border border-amber-300/40 px-3 py-1.5 text-amber-300">{item.content_origin === 'community' ? 'Community shared' : 'Reviewed source'}</span>
    <span className="ml-auto text-slate-400" aria-label={`Video ${position} of ${total}`}>{position} / {total}</span>
    <span className="basis-full text-amber-300">Watch · <Link className="underline decoration-amber-300/60 underline-offset-4 outline-none hover:text-amber-200 focus-visible:ring-4 focus-visible:ring-amber-300/70" to={`/issues/${item.issue.slug}`} state={{ returnToVideoId: item.video_id }}>{item.issue.title}</Link></span>
  </div>;
}

function ScrollCue({ last }: { last: boolean }) {
  if (last) return null;
  return <div className="mt-5 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-slate-400" aria-hidden="true">
    <ChevronDown className="h-4 w-4 motion-safe:animate-bounce" /> Scroll for next video
  </div>;
}

function NarrativePanel({ item, dark = false }: { item: Video; dark?: boolean }) {
  if (!item.transcript && !item.accessibility?.official_transcript_url) return null;
  const label = item.accessibility?.text_kind === 'overview' ? 'Overview' : 'Transcript';
  const overviewPoints = item.accessibility?.text_kind === 'overview' ? item.accessibility.overview_points || [] : [];
  return <details className={`mt-4 rounded-xl p-4 ${dark ? 'bg-black/70' : 'bg-white/10'}`} open>
    <summary className="cursor-pointer font-semibold">{label}</summary>
    {overviewPoints.length > 0
      ? <ul className="mt-3 list-disc space-y-2 pl-5 leading-6 text-slate-100">{overviewPoints.map((point) => <li key={point}>{point}</li>)}</ul>
      : item.transcript && <p className="mt-2 leading-7 text-slate-100">{item.transcript}</p>}
    {item.accessibility?.official_transcript_url && <a className="mt-3 inline-block font-semibold text-amber-300 underline" href={item.accessibility.official_transcript_url} target="_blank" rel="noreferrer">{item.accessibility.official_transcript_label} <ExternalLink className="inline h-4 w-4" /></a>}
  </details>;
}

function OfficialEmbedCard({ item, active, autoPlayRequested, embed, position, total, onChange, onComments }: { item: Video; active: boolean; autoPlayRequested: boolean; embed: Delivery; position: number; total: number; onChange: (next: Video) => void; onComments: () => void }) {
  const [consented, setConsented] = useState(autoPlayRequested);
  const [failed, setFailed] = useState(false);
  const [posterFailed, setPosterFailed] = useState(false);
  const provider = getValidatedProvider(embed);
  const embedUrl = getOfficialEmbedUrl(embed);
  const playerLoaded = active && consented;
  if (!provider || !embedUrl) return <LinkOutCard item={item} delivery={embed} position={position} total={total} onChange={onChange} onComments={onComments} />;
  const providerLabel = getProviderLabel(provider);
  const privacyLine = `Playing connects to ${providerLabel}`;
  const posterUrl = embed.poster_url?.startsWith('/videos/') ? `${getApiBaseUrl()}${embed.poster_url}` : embed.poster_url;
  return <article data-video-id={item.video_id} className="min-h-screen snap-start bg-[#070b14] text-white" aria-current={active ? 'true' : undefined} aria-label={`${item.creator_label}. ${item.caption}`}>
    <div className="mx-auto grid min-h-screen max-w-6xl items-center gap-6 px-4 py-8 lg:grid-cols-[minmax(320px,0.82fr)_minmax(340px,1fr)] lg:px-8">
      <div className="relative mx-auto aspect-[9/16] max-h-[72vh] w-full max-w-md overflow-hidden rounded-3xl border border-white/15 bg-[#111827] text-center shadow-2xl shadow-black/40">
        <ActionRail item={item} onChange={onChange} onComments={onComments} />
        {playerLoaded && !failed ? <iframe
          className="absolute inset-0 h-full w-full"
          src={embedUrl}
          title={`${item.caption} — ${embed.source_label}`}
          referrerPolicy="strict-origin-when-cross-origin"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          allowFullScreen
          onError={() => setFailed(true)}
        /> : <div className="absolute inset-0 flex flex-col items-center justify-center overflow-hidden bg-gradient-to-b from-slate-800 to-slate-950 p-8">
          {posterUrl && !posterFailed && <img src={posterUrl} alt="" aria-hidden="true" className="absolute inset-0 h-full w-full object-cover" onError={() => setPosterFailed(true)} />}
          <div className="absolute inset-0 bg-gradient-to-b from-black/45 via-black/60 to-black/90" />
          <div className="relative z-[1] flex flex-col items-center">
          <p className="text-sm font-bold uppercase tracking-widest text-amber-300">{embed.source_label || providerLabel}</p>
          <h2 className="mt-3 line-clamp-3 text-2xl font-bold">{failed ? 'Inline player unavailable' : item.caption}</h2>
          {active && !failed && <button aria-label={`Play video from ${providerLabel}`} className="mt-7 grid h-20 w-20 place-content-center rounded-full bg-white text-slate-950 shadow-xl outline-none transition hover:scale-105 focus-visible:ring-4 focus-visible:ring-amber-300/70" onClick={() => setConsented(true)}><Play className="ml-1 h-9 w-9 fill-current" aria-hidden="true" /></button>}
          <p className="mt-5 text-sm text-slate-300">{privacyLine}. <a className="text-amber-300 underline" href={getProviderPrivacyUrl(provider)} target="_blank" rel="noreferrer">Privacy details</a></p>
          {!active && consented && <p className="mt-4 text-slate-400">The player was unloaded because this card is not active.</p>}
          <a className="mt-4 block text-sm font-semibold text-amber-300 underline" href={embed.canonical_url} target="_blank" rel="noreferrer">Watch at the official source instead</a>
          </div>
        </div>}
      </div>
      <div className="min-w-0 py-3 lg:py-6">
        <WatchStatus item={item} provider={providerLabel} position={position} total={total} />
        <h1 className="mt-3 text-2xl font-bold sm:text-4xl">{item.caption}</h1>
        <NarrativePanel item={item} />
        <CivicActions item={item} />
        <ScrollCue last={position === total} />
      </div>
    </div>
  </article>;
}

function LinkOutCard({ item, delivery, position, total, onChange, onComments }: { item: Video; delivery: Delivery; position: number; total: number; onChange: (next: Video) => void; onComments: () => void }) {
  return <article data-video-id={item.video_id} className="min-h-screen snap-start bg-[#070b14] text-white" aria-label={`${item.creator_label}. ${item.caption}`}>
    <div className="relative mx-auto flex min-h-screen max-w-5xl flex-col justify-center px-4 py-8 pr-24 sm:px-8 sm:pr-28">
      <ActionRail item={item} onChange={onChange} onComments={onComments} />
      <WatchStatus item={item} provider={delivery.source_label || 'Official source'} position={position} total={total} />
      <p className="mt-3 text-sm font-bold uppercase tracking-widest text-slate-400">{delivery.development_only ? 'Development Watch fixture' : item.content_origin === 'community' ? 'Shared by a community member' : 'Reviewed production source'}</p>
      <h1 className="mt-3 text-2xl font-bold sm:text-4xl">{item.caption}</h1>
      <p className="mt-4 leading-7 text-slate-300">Inline playback is unavailable. The overview, official transcript, source, and civic context remain available.</p>
      <a className="mt-5 w-fit rounded-full bg-white px-5 py-3 font-bold text-slate-950" href={delivery.canonical_url} target="_blank" rel="noreferrer">Watch at the official source instead</a>
      <NarrativePanel item={item} />
      <CivicActions item={item} />
      <ScrollCue last={position === total} />
    </div>
  </article>;
}

function NativeVideoCard({ item, active, reducedMotion, onActive, position, total, onChange, onComments }: { item: Video; active: boolean; reducedMotion: boolean; onActive: () => void; position: number; total: number; onChange: (next: Video) => void; onComments: () => void }) {
  const video = useRef<HTMLVideoElement>(null);
  const [muted, setMuted] = useState(true);
  const [manualPause, setManualPause] = useState(false);
  const [unavailable, setUnavailable] = useState(false);
  useEffect(() => {
    const node = video.current;
    if (!node) return;
    if (active && !reducedMotion && !manualPause && !document.hidden) void node.play().catch(() => setManualPause(true));
    else node.pause();
  }, [active, reducedMotion, manualPause]);
  return <article data-video-id={item.video_id} className="relative min-h-screen snap-start overflow-hidden bg-[#070b14] text-white" aria-label={`${item.creator_label}. ${item.caption}`}>
    <ActionRail item={item} onChange={onChange} onComments={onComments} />
    {!unavailable ? <video ref={video} className="absolute inset-0 h-full w-full object-cover" src={item.media_url} muted={muted} loop playsInline preload={active ? 'auto' : 'metadata'} onError={() => setUnavailable(true)} onClick={onActive} /> :
      <div className="absolute inset-0 grid place-content-center p-8 text-center" role="alert"><h2 className="text-2xl font-bold">Video unavailable</h2><p className="mt-2 text-slate-300">The transcript and official evidence remain available.</p></div>}
    <div className="absolute inset-0 bg-gradient-to-t from-black via-black/25 to-black/10" />
    <div className="absolute inset-x-0 bottom-0 mx-auto max-w-4xl p-6 pb-12 sm:p-10">
      <WatchStatus item={item} provider="Hosted video" position={position} total={total} />
      <p className="mt-3 text-sm font-bold uppercase tracking-widest text-slate-300">Development Watch fixture</p>
      <h1 className="mt-3 text-2xl font-bold sm:text-4xl">{item.caption}</h1>
      <NarrativePanel item={item} dark />
      <div className="mt-5 flex flex-wrap gap-3">
        <button className="rounded-full bg-white px-4 py-3 font-bold text-slate-950" onClick={() => { onActive(); setManualPause((v) => !v); }}>{active && !manualPause ? <Pause className="inline h-4 w-4" /> : <Play className="inline h-4 w-4" />} <span className="ml-1">{active && !manualPause ? 'Pause' : 'Play'}</span></button>
        <button className="rounded-full bg-white px-4 py-3 font-bold text-slate-950" onClick={() => setMuted((v) => !v)}>{muted ? <VolumeX className="inline h-4 w-4" /> : <Volume2 className="inline h-4 w-4" />} <span className="ml-1">{muted ? 'Unmute' : 'Mute'}</span></button>
        <CivicActions item={item} />
      </div>
    </div>
  </article>;
}

function VideoCard(props: { item: Video; active: boolean; autoPlayRequested: boolean; reducedMotion: boolean; onActive: () => void; onChange: (next: Video) => void; onComments: () => void; position: number; total: number }) {
  const delivery = props.item.delivery;
  if (delivery?.mode === 'official_embed') {
    const authorized = (!delivery.development_only || DEVELOPMENT_EMBED_AUTHORIZED)
      && Boolean(getOfficialEmbedUrl(delivery));
    return authorized
      ? <OfficialEmbedCard item={props.item} active={props.active} autoPlayRequested={props.autoPlayRequested} embed={delivery} position={props.position} total={props.total} onChange={props.onChange} onComments={props.onComments} />
      : <LinkOutCard item={props.item} delivery={delivery} position={props.position} total={props.total} onChange={props.onChange} onComments={props.onComments} />;
  }
  if (delivery?.mode === 'link_out') return <LinkOutCard item={props.item} delivery={delivery} position={props.position} total={props.total} onChange={props.onChange} onComments={props.onComments} />;
  return <NativeVideoCard {...props} />;
}

function CivicFallbackCard({ item }: { item: CivicFallback }) {
  if (item.kind === 'agenda') return <article data-feed-id={item.key} className="min-h-screen snap-start bg-[#0b1220] text-white">
    <div className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center px-6 py-24">
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-amber-300">Civic context · Agenda issue</p>
      <h2 className="mt-4 text-3xl font-bold sm:text-5xl">{item.title}</h2>
      {item.summary && <p className="mt-5 text-lg leading-8 text-slate-200">{item.summary}</p>}
      {item.evidenceNote && <p className="mt-5 rounded-2xl bg-white/10 p-5 leading-7 text-slate-100"><span className="font-bold text-amber-300">Reviewed evidence:</span> {item.evidenceNote}</p>}
      <p className="mt-4 text-sm text-slate-400">{item.billCount} linked {item.billCount === 1 ? 'bill' : 'bills'} in WTP.</p>
      <Link className="mt-7 inline-flex min-h-12 w-fit items-center rounded-full bg-amber-300 px-6 font-bold text-slate-950" to={`/issues/${item.slug}`}>Explore this issue</Link>
    </div>
  </article>;
  return <article data-feed-id={item.key} className="min-h-screen snap-start bg-[#111827] text-white">
    <div className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center px-6 py-24">
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-sky-300">Civic context · Legislation</p>
      <h2 className="mt-4 text-3xl font-bold sm:text-5xl">{item.title}</h2>
      <p className="mt-4 font-semibold text-amber-300">{item.billId.toUpperCase()}</p>
      {item.latestAction && <p className="mt-5 rounded-2xl bg-white/10 p-5 leading-7 text-slate-100"><span className="font-bold">Latest official action:</span> {item.latestAction}</p>}
      {item.latestActionDate && <p className="mt-3 text-sm text-slate-400">Action date: {item.latestActionDate}</p>}
      <Link className="mt-7 inline-flex min-h-12 w-fit items-center rounded-full bg-white px-6 font-bold text-slate-950" to={`/politics/bill/${item.billId}`}>Read the bill record</Link>
    </div>
  </article>;
}

const VIDEO_PAGE_SIZE = 6;
const CIVIC_PAGE_SIZE = 10;

export default function WatchVideoPage() {
  const { videoId } = useParams();
  const location = useLocation();
  const initialVideoId = useRef(videoId || '');
  const autoPlayVideoId = useRef(new URLSearchParams(location.search).get('play') === '1' ? (videoId || '') : '');
  const observerRouteId = useRef('');
  const lastScrolledRouteId = useRef('');
  const navigate = useNavigate();
  const { authedFetch } = useAuth();
  const [videos, setVideos] = useState<Video[]>([]);
  const [activeId, setActiveId] = useState(videoId || '');
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState('');
  const [continuationError, setContinuationError] = useState('');
  const [nextVideoCursor, setNextVideoCursor] = useState<string | null>(null);
  const [videoCatalogExhausted, setVideoCatalogExhausted] = useState(false);
  const [fallbacks, setFallbacks] = useState<CivicFallback[]>([]);
  const [agendaLoaded, setAgendaLoaded] = useState(false);
  const [billOffset, setBillOffset] = useState(0);
  const [billCatalogExhausted, setBillCatalogExhausted] = useState(false);
  const [loadingContinuation, setLoadingContinuation] = useState(false);
  const [commentsVideoId, setCommentsVideoId] = useState(() => new URLSearchParams(location.search).get('comments') === '1' ? (videoId || '') : '');
  const commentsTrigger = useRef<HTMLElement | null>(null);
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const updateVideo = (next: Video) => setVideos((current) => current.map((item) => item.video_id === next.video_id ? next : item));
  const openComments = (item: Video) => {
    commentsTrigger.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setCommentsVideoId(item.video_id);
  };
  const closeComments = () => {
    setCommentsVideoId('');
    window.setTimeout(() => commentsTrigger.current?.focus(), 0);
  };
  useEffect(() => {
    const controller = new AbortController();
    const loadFeed = async () => {
      const feedResponse = await authedFetch(`${getApiBaseUrl()}/videos?limit=${VIDEO_PAGE_SIZE}`, { signal: controller.signal });
      if (!feedResponse.ok) throw new Error('Watch could not load');
      const feed = await feedResponse.json() as Feed;
      let items = feed.videos;
      const requestedId = initialVideoId.current;
      if (requestedId && !items.some((item) => item.video_id === requestedId)) {
        const exactResponse = await authedFetch(`${getApiBaseUrl()}/videos/${encodeURIComponent(requestedId)}`, { signal: controller.signal });
        if (exactResponse.status === 404) throw new Error('This civic video is unavailable.');
        if (!exactResponse.ok) throw new Error('Watch could not load');
        const exact = await exactResponse.json() as Video;
        items = [exact, ...items];
      }
      setVideos(items);
      setNextVideoCursor(feed.next_cursor);
      setVideoCatalogExhausted(!feed.has_more);
      setActiveId(requestedId || items[0]?.video_id || '');
      setLoaded(true);
    };
    void loadFeed().catch((e) => { if (e.name !== 'AbortError') { setError(e.message); setLoaded(true); } });
    return () => controller.abort();
  }, [authedFetch]);
  const appendUniqueVideos = useCallback((incoming: Video[]) => {
    setVideos((current) => {
      const seen = new Set(current.map((item) => item.video_id));
      return [...current, ...incoming.filter((item) => !seen.has(item.video_id))];
    });
  }, []);
  const appendUniqueFallbacks = useCallback((incoming: CivicFallback[]) => {
    setFallbacks((current) => {
      const seen = new Set(current.map((item) => item.key));
      return [...current, ...incoming.filter((item) => !seen.has(item.key))];
    });
  }, []);
  const loadContinuation = useCallback(async () => {
    if (loadingContinuation || billCatalogExhausted) return;
    setLoadingContinuation(true);
    setContinuationError('');
    try {
      if (!videoCatalogExhausted && nextVideoCursor) {
        const response = await authedFetch(`${getApiBaseUrl()}/videos?limit=${VIDEO_PAGE_SIZE}&cursor=${encodeURIComponent(nextVideoCursor)}`);
        if (!response.ok) throw new Error('More civic videos are temporarily unavailable.');
        const page = await response.json() as Feed;
        appendUniqueVideos(page.videos);
        setNextVideoCursor(page.next_cursor);
        setVideoCatalogExhausted(!page.has_more);
        return;
      }
      if (!agendaLoaded) {
        const response = await authedFetch(`${getApiBaseUrl()}/issues`);
        if (!response.ok) throw new Error('Civic issue context is temporarily unavailable.');
        const agenda = await response.json() as { items?: Array<{ slug: string; title: string; summary?: string | null; evidence_note?: string | null; bill_count?: number }> };
        appendUniqueFallbacks((agenda.items || []).map((item) => ({
          kind: 'agenda', key: `agenda:${item.slug}`, slug: item.slug, title: item.title,
          summary: item.summary || null, evidenceNote: item.evidence_note || null, billCount: item.bill_count || 0,
        })));
        setAgendaLoaded(true);
        return;
      }
      const response = await authedFetch(`${getApiBaseUrl()}/politics/bills?limit=${CIVIC_PAGE_SIZE}&offset=${billOffset}`);
      if (!response.ok) throw new Error('Legislation is temporarily unavailable.');
      const page = await response.json() as { total: number; bills?: Array<{ bill_id: string; title?: string | null; latest_action_text?: string | null; latest_action_date?: string | null }> };
      const bills = page.bills || [];
      appendUniqueFallbacks(bills.map((bill) => ({
        kind: 'bill', key: `bill:${bill.bill_id}`, billId: bill.bill_id,
        title: bill.title || bill.bill_id.toUpperCase(), latestAction: bill.latest_action_text || null,
        latestActionDate: bill.latest_action_date || null,
      })));
      const nextOffset = billOffset + bills.length;
      setBillOffset(nextOffset);
      setBillCatalogExhausted(bills.length === 0 || nextOffset >= page.total);
    } catch (reason) {
      setContinuationError(reason instanceof Error ? reason.message : 'More civic material is temporarily unavailable.');
    } finally {
      setLoadingContinuation(false);
    }
  }, [agendaLoaded, appendUniqueFallbacks, appendUniqueVideos, authedFetch, billCatalogExhausted, billOffset, loadingContinuation, nextVideoCursor, videoCatalogExhausted]);
  useEffect(() => {
    if (!loaded || error || billCatalogExhausted) return;
    if (!videos.length || (videoCatalogExhausted && fallbacks.length === 0)) void loadContinuation();
  }, [billCatalogExhausted, error, fallbacks.length, loadContinuation, loaded, videoCatalogExhausted, videos.length]);
  useEffect(() => {
    if (!videos.length) return;
    const observer = new IntersectionObserver((entries) => { const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0]; if (visible) { const id = (visible.target as HTMLElement).dataset.videoId || ''; if (!id) return; setActiveId(id); observerRouteId.current = id; navigate(`/videos/${id}`, { replace: true }); } }, { threshold: [0.6] });
    document.querySelectorAll('[data-video-id]').forEach((node) => observer.observe(node));
    return () => observer.disconnect();
  }, [videos, navigate]);
  useEffect(() => {
    if (!loaded || !videoId || !videos.length) return;
    if (observerRouteId.current === videoId) {
      observerRouteId.current = '';
      return;
    }
    if (lastScrolledRouteId.current === videoId) return;
    const requested = Array.from(document.querySelectorAll<HTMLElement>('[data-video-id]')).find((node) => node.dataset.videoId === videoId);
    const feedViewport = requested?.closest<HTMLElement>('[aria-label="Civic video feed"]');
    if (requested && feedViewport) feedViewport.scrollTo({ top: requested.offsetTop, behavior: 'auto' });
    lastScrolledRouteId.current = videoId;
  }, [loaded, videoId, videos]);
  if (error) return <main className="min-h-screen bg-[#070b14] p-12 text-white" role="alert"><h1 className="text-3xl font-bold">{error}</h1></main>;
  if (!loaded) return <main className="min-h-screen bg-[#070b14] p-12 text-center text-white">Loading Watch…</main>;
  if (!videos.length && !fallbacks.length && loadingContinuation) return <main className="min-h-screen bg-[#070b14] p-12 text-center text-white">Loading real civic material…</main>;
  if (!videos.length && !fallbacks.length) return <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-[#070b14] p-4 text-center text-white"><WatchQuickComposer /><h1 className="mt-5 text-3xl font-bold">Civic material is temporarily unavailable.</h1><p className="max-w-xl text-slate-300">Nothing synthetic will be inserted. Try the live civic records again.</p><button type="button" className="rounded-full bg-amber-300 px-5 py-3 font-bold text-slate-950" onClick={() => void loadContinuation()}>Try again</button></main>;
  const commentsVideo = videos.find((item) => item.video_id === commentsVideoId) || null;
  return <><main onScroll={(event) => { const node = event.currentTarget; if (node.scrollHeight - node.scrollTop - node.clientHeight < node.clientHeight * 2) void loadContinuation(); }} className="relative h-screen snap-y snap-proximity overflow-y-auto overscroll-y-contain bg-[#070b14]" aria-label="Civic video feed"><div className="absolute inset-x-0 top-3 z-30"><WatchQuickComposer /></div>{videos.map((item, index) => <VideoCard key={item.video_id} item={item} active={activeId === item.video_id} autoPlayRequested={autoPlayVideoId.current === item.video_id} reducedMotion={reducedMotion} onActive={() => setActiveId(item.video_id)} onChange={updateVideo} onComments={() => openComments(item)} position={index + 1} total={videos.length} />)}{fallbacks.map((item) => <CivicFallbackCard key={item.key} item={item} />)}{(loadingContinuation || continuationError || billCatalogExhausted) && <section className="snap-start bg-[#070b14] px-6 py-8 text-center text-sm text-slate-300" aria-live="polite">{loadingContinuation ? 'Loading more real civic material…' : continuationError ? <><p>{continuationError} Already-loaded items remain available.</p><button type="button" className="mt-3 rounded-full border border-amber-300 px-4 py-2 font-bold text-amber-300" onClick={() => void loadContinuation()}>Try again</button></> : <><p>You are caught up with the available real feed.</p><Link className="mt-3 inline-block font-bold text-amber-300 underline" to="/civic">Explore the full Civic Hub</Link></>}</section>}</main>{commentsVideo && <VideoCommentsPanel videoId={commentsVideo.video_id} videoCaption={commentsVideo.caption} open onClose={closeComments} />}</>;
}
