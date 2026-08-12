import { useEffect, useRef, useState } from 'react';
import { Bookmark, ChevronDown, ExternalLink, Heart, MessageCircle, Pause, Play, Volume2, VolumeX } from 'lucide-react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { getApiBaseUrl } from '../api/client';
import IssueActionStrip from '../components/IssueActionStrip';
import ShareButton from '../components/ShareButton';
import { useAuth } from '../contexts/AuthContext';
import { getOfficialEmbedUrl, getProviderLabel, getProviderPrivacyUrl, getValidatedProvider } from '../features/watch/providers';

type Video = {
  video_id: string; creator_label: string; caption: string; transcript: string | null;
  media_url: string; published_at: string;
  delivery: Delivery | null;
  accessibility: Accessibility | null;
  source: { url: string; publisher: string }; issue: { slug: string; title: string };
  bills: Array<{ bill_id: string; title: string | null }>;
  discussion_post_id: number | null;
  like_count: number; discussion_count: number; liked: boolean; saved: boolean;
};
type Feed = { videos: Video[]; next_cursor: string | null; has_more: boolean };

type Delivery = {
  mode: 'official_embed' | 'hosted_video' | 'link_out'; provider: string | null;
  provider_video_id: string | null; canonical_url: string; source_label: string | null;
  development_only: boolean;
};

type Accessibility = {
  text_kind: 'overview' | 'transcript'; official_transcript_url: string;
  official_transcript_label: string; overview_points?: string[]; development_only: boolean;
};

const DEVELOPMENT_EMBED_AUTHORIZED = import.meta.env.DEV && import.meta.env.VITE_ENABLE_DEVELOPMENT_WATCH_EMBED === 'true';

function CivicActions({ item }: { item: Video }) {
  return <div className="mt-5 min-w-0">
    <IssueActionStrip issueSlug={item.issue.slug} returnToVideoId={item.video_id} />
    <div aria-label="Video sources" className="mt-3 flex flex-wrap gap-3 [&_a]:rounded-full [&_a]:bg-white/90 [&_a]:px-4 [&_a]:py-3 [&_a]:font-bold [&_a]:text-slate-950 [&_a]:outline-none [&_a]:focus-visible:ring-4 [&_a]:focus-visible:ring-amber-300/70">
      <a href={item.source.url} target="_blank" rel="noreferrer">{item.source.publisher} <ExternalLink className="inline h-4 w-4" /></a>
      {item.bills.map((bill) => <Link key={bill.bill_id} to={`/politics/bill/${bill.bill_id}`} state={{ returnToVideoId: item.video_id }}>{bill.bill_id.toUpperCase()}</Link>)}
    </div>
  </div>;
}

function ActionRail({ item, onChange }: { item: Video; onChange: (next: Video) => void }) {
  const { isAuthenticated, authedFetch } = useAuth();
  const navigate = useNavigate();
  const [busy, setBusy] = useState<'like' | 'save' | ''>('');
  const [message, setMessage] = useState('');
  const signIn = () => navigate(`/login?next=${encodeURIComponent(`/watch/${item.video_id}`)}`);
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
  const discussTo = item.discussion_post_id ? `/discuss/${item.discussion_post_id}` : `/discuss?video=${encodeURIComponent(item.video_id)}`;
  const buttonClass = 'grid min-h-14 min-w-14 place-items-center gap-1 rounded-full bg-black/65 p-2 text-xs font-bold text-white outline-none transition focus-visible:ring-4 focus-visible:ring-amber-300/70 disabled:opacity-60';
  return <aside className="absolute bottom-5 right-3 z-10 flex flex-col gap-3 sm:right-5" aria-label="Video actions">
    <button type="button" className={buttonClass} aria-label={`${item.liked ? 'Unlike' : 'Like'} video, ${item.like_count} likes`} aria-pressed={item.liked} disabled={busy === 'like'} onClick={() => void toggle('like')}><Heart className={`h-6 w-6 ${item.liked ? 'fill-rose-500 text-rose-500' : ''}`} aria-hidden="true" /><span aria-live="polite">{item.like_count}</span></button>
    <button type="button" className={buttonClass} aria-label={item.saved ? 'Remove video from private saved collection' : 'Save video privately'} aria-pressed={item.saved} disabled={busy === 'save'} onClick={() => void toggle('save')}><Bookmark className={`h-6 w-6 ${item.saved ? 'fill-amber-300 text-amber-300' : ''}`} aria-hidden="true" /><span>Save</span></button>
    <Link className={buttonClass} aria-label={`Discuss this video, ${item.discussion_count} published contributions`} to={discussTo} state={{ returnToVideoId: item.video_id }}><MessageCircle className="h-6 w-6" aria-hidden="true" /><span>{item.discussion_count}</span></Link>
    <ShareButton rail url={`${window.location.origin}/watch/${item.video_id}`} title={item.caption} text={item.caption} />
    <span className="sr-only" role="status" aria-live="polite">{message}</span>
  </aside>;
}

function WatchStatus({ item, provider, position, total }: { item: Video; provider: string; position: number; total: number }) {
  return <div className="flex flex-wrap items-center gap-2 text-xs font-bold uppercase tracking-widest">
    <span className="rounded-full bg-white/10 px-3 py-1.5 text-white">{provider}</span>
    <span className="rounded-full border border-amber-300/40 px-3 py-1.5 text-amber-300">Reviewed source</span>
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

function OfficialEmbedCard({ item, active, embed, position, total, onChange }: { item: Video; active: boolean; embed: Delivery; position: number; total: number; onChange: (next: Video) => void }) {
  const [consented, setConsented] = useState(false);
  const [failed, setFailed] = useState(false);
  const provider = getValidatedProvider(embed);
  const embedUrl = getOfficialEmbedUrl(embed);
  const playerLoaded = active && consented;
  if (!provider || !embedUrl) return <LinkOutCard item={item} delivery={embed} position={position} total={total} onChange={onChange} />;
  const providerLabel = getProviderLabel(provider);
  const privacyLine = `Playing connects to ${providerLabel}`;
  return <article data-video-id={item.video_id} className="min-h-screen snap-start bg-[#070b14] text-white" aria-current={active ? 'true' : undefined} aria-label={`${item.creator_label}. ${item.caption}`}>
    <div className="mx-auto grid min-h-screen max-w-6xl items-center gap-6 px-4 py-8 lg:grid-cols-[minmax(320px,0.82fr)_minmax(340px,1fr)] lg:px-8">
      <div className="relative mx-auto grid aspect-[9/16] max-h-[72vh] w-full max-w-md place-content-center overflow-hidden rounded-3xl border border-white/15 bg-[#111827] text-center shadow-2xl shadow-black/40">
        <ActionRail item={item} onChange={onChange} />
        {playerLoaded && !failed ? <iframe
          className="absolute inset-0 h-full w-full"
          src={embedUrl}
          title={`${item.caption} — ${embed.source_label}`}
          referrerPolicy="strict-origin-when-cross-origin"
          allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          allowFullScreen
          onError={() => setFailed(true)}
        /> : <div className="flex h-full max-w-2xl flex-col items-center justify-center bg-gradient-to-b from-slate-800 to-slate-950 p-8">
          <p className="text-sm font-bold uppercase tracking-widest text-amber-300">{embed.source_label || providerLabel}</p>
          <h2 className="mt-3 line-clamp-3 text-2xl font-bold">{failed ? 'Inline player unavailable' : item.caption}</h2>
          {active && !failed && <button aria-label={`Play video from ${providerLabel}`} className="mt-7 grid h-20 w-20 place-content-center rounded-full bg-white text-slate-950 shadow-xl outline-none transition hover:scale-105 focus-visible:ring-4 focus-visible:ring-amber-300/70" onClick={() => setConsented(true)}><Play className="ml-1 h-9 w-9 fill-current" aria-hidden="true" /></button>}
          <p className="mt-5 text-sm text-slate-300">{privacyLine}. <a className="text-amber-300 underline" href={getProviderPrivacyUrl(provider)} target="_blank" rel="noreferrer">Privacy details</a></p>
          {!active && consented && <p className="mt-4 text-slate-400">The player was unloaded because this card is not active.</p>}
          <a className="mt-4 block text-sm font-semibold text-amber-300 underline" href={embed.canonical_url} target="_blank" rel="noreferrer">Watch at the official source instead</a>
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

function LinkOutCard({ item, delivery, position, total, onChange }: { item: Video; delivery: Delivery; position: number; total: number; onChange: (next: Video) => void }) {
  return <article data-video-id={item.video_id} className="min-h-screen snap-start bg-[#070b14] text-white" aria-label={`${item.creator_label}. ${item.caption}`}>
    <div className="relative mx-auto flex min-h-screen max-w-5xl flex-col justify-center px-4 py-8 pr-24 sm:px-8 sm:pr-28">
      <ActionRail item={item} onChange={onChange} />
      <WatchStatus item={item} provider={delivery.source_label || 'Official source'} position={position} total={total} />
      <p className="mt-3 text-sm font-bold uppercase tracking-widest text-slate-400">Development Watch fixture</p>
      <h1 className="mt-3 text-2xl font-bold sm:text-4xl">{item.caption}</h1>
      <p className="mt-4 leading-7 text-slate-300">Inline playback is unavailable. The overview, official transcript, source, and civic context remain available.</p>
      <a className="mt-5 w-fit rounded-full bg-white px-5 py-3 font-bold text-slate-950" href={delivery.canonical_url} target="_blank" rel="noreferrer">Watch at the official source instead</a>
      <NarrativePanel item={item} />
      <CivicActions item={item} />
      <ScrollCue last={position === total} />
    </div>
  </article>;
}

function NativeVideoCard({ item, active, reducedMotion, onActive, position, total, onChange }: { item: Video; active: boolean; reducedMotion: boolean; onActive: () => void; position: number; total: number; onChange: (next: Video) => void }) {
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
    <ActionRail item={item} onChange={onChange} />
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

function VideoCard(props: { item: Video; active: boolean; reducedMotion: boolean; onActive: () => void; onChange: (next: Video) => void; position: number; total: number }) {
  const delivery = props.item.delivery;
  if (delivery?.mode === 'official_embed') {
    const authorized = (!delivery.development_only || DEVELOPMENT_EMBED_AUTHORIZED)
      && Boolean(getOfficialEmbedUrl(delivery));
    return authorized
      ? <OfficialEmbedCard item={props.item} active={props.active} embed={delivery} position={props.position} total={props.total} onChange={props.onChange} />
      : <LinkOutCard item={props.item} delivery={delivery} position={props.position} total={props.total} onChange={props.onChange} />;
  }
  if (delivery?.mode === 'link_out') return <LinkOutCard item={props.item} delivery={delivery} position={props.position} total={props.total} onChange={props.onChange} />;
  return <NativeVideoCard {...props} />;
}

export default function WatchVideoPage() {
  const { videoId } = useParams();
  const navigate = useNavigate();
  const { authedFetch } = useAuth();
  const [videos, setVideos] = useState<Video[]>([]);
  const [activeId, setActiveId] = useState(videoId || '');
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState('');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const updateVideo = (next: Video) => setVideos((current) => current.map((item) => item.video_id === next.video_id ? next : item));
  useEffect(() => {
    const controller = new AbortController();
    const loadFeed = async () => {
      const feedResponse = await authedFetch(`${getApiBaseUrl()}/videos?limit=25`, { signal: controller.signal });
      if (!feedResponse.ok) throw new Error('Watch could not load');
      const feed = await feedResponse.json() as Feed;
      let items = feed.videos;
      if (videoId && !items.some((item) => item.video_id === videoId)) {
        const exactResponse = await authedFetch(`${getApiBaseUrl()}/videos/${encodeURIComponent(videoId)}`, { signal: controller.signal });
        if (exactResponse.status === 404) throw new Error('This civic video is unavailable.');
        if (!exactResponse.ok) throw new Error('Watch could not load');
        const exact = await exactResponse.json() as Video;
        items = [exact, ...items];
      }
      setVideos(items);
      setActiveId(videoId || items[0]?.video_id || '');
      setLoaded(true);
    };
    void loadFeed().catch((e) => { if (e.name !== 'AbortError') { setError(e.message); setLoaded(true); } });
    return () => controller.abort();
  }, [videoId, authedFetch]);
  useEffect(() => {
    if (!videos.length) return;
    const observer = new IntersectionObserver((entries) => { const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0]; if (visible) { const id = (visible.target as HTMLElement).dataset.videoId || ''; setActiveId(id); navigate(`/watch/${id}`, { replace: true }); } }, { threshold: [0.6] });
    document.querySelectorAll('[data-video-id]').forEach((node) => observer.observe(node));
    const requested = Array.from(document.querySelectorAll<HTMLElement>('[data-video-id]')).find((node) => node.dataset.videoId === videoId); requested?.scrollIntoView();
    return () => observer.disconnect();
  }, [videos, videoId, navigate]);
  if (error) return <main className="min-h-screen bg-[#070b14] p-12 text-white" role="alert"><h1 className="text-3xl font-bold">{error}</h1></main>;
  if (!loaded) return <main className="min-h-screen bg-[#070b14] p-12 text-center text-white">Loading Watch…</main>;
  if (!videos.length) return <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-[#070b14] p-12 text-center text-white"><h1 className="text-3xl font-bold">No civic videos are published yet.</h1><p className="max-w-xl text-slate-300">Watch will show reviewed civic videos with evidence, issue, and bill links.</p><Link className="font-semibold text-sky-300 underline" to="/civic">Explore the Civic Hub</Link></main>;
  return <main className="h-screen snap-y snap-mandatory overflow-y-auto bg-[#070b14]" aria-label="Civic video feed">{videos.map((item, index) => <VideoCard key={item.video_id} item={item} active={activeId === item.video_id} reducedMotion={reducedMotion} onActive={() => setActiveId(item.video_id)} onChange={updateVideo} position={index + 1} total={videos.length} />)}</main>;
}
