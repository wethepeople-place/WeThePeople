import { useEffect, useRef, useState } from 'react';
import { ExternalLink, Pause, Play, Volume2, VolumeX } from 'lucide-react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { getApiBaseUrl } from '../api/client';
import ShareButton from '../components/ShareButton';

type Video = {
  video_id: string; creator_label: string; caption: string; transcript: string | null;
  media_url: string; published_at: string;
  source: { url: string; publisher: string }; issue: { slug: string; title: string };
  bills: Array<{ bill_id: string; title: string | null }>;
  discussion_post_id: number | null;
};
type Feed = { videos: Video[]; next_cursor: string | null; has_more: boolean };

type DevelopmentEmbed = {
  provider: 'youtube'; providerVideoId: string; canonicalUrl: string; sourceLabel: string;
};

const DEVELOPMENT_EMBEDS: Record<string, DevelopmentEmbed> = import.meta.env.DEV && import.meta.env.VITE_ENABLE_DEVELOPMENT_WATCH_EMBED === 'true' ? {
  'housing-rent-why-rents-move': {
    provider: 'youtube',
    providerVideoId: '-Zfh6IKiJ4s',
    canonicalUrl: 'https://www.youtube.com/watch?v=-Zfh6IKiJ4s',
    sourceLabel: 'U.S. Census Bureau',
  },
} : {};

function CivicActions({ item }: { item: Video }) {
  return <div className="mt-5 flex flex-wrap gap-3">
    <ShareButton url={`${window.location.origin}/watch/${item.video_id}`} title={item.caption} text={item.caption} />
    <Link className="rounded-full bg-amber-400 px-4 py-3 font-bold text-slate-950" to={`/issues/${item.issue.slug}`} state={{ returnToVideoId: item.video_id }}>Evidence</Link>
    <a className="rounded-full bg-white/90 px-4 py-3 font-bold text-slate-950" href={item.source.url} target="_blank" rel="noreferrer">{item.source.publisher} <ExternalLink className="inline h-4 w-4" /></a>
    {item.bills.map((bill) => <Link key={bill.bill_id} className="rounded-full bg-white/90 px-4 py-3 font-bold text-slate-950" to={`/politics/bill/${bill.bill_id}`} state={{ returnToVideoId: item.video_id }}>{bill.bill_id.toUpperCase()}</Link>)}
    {item.discussion_post_id && <Link className="rounded-full bg-amber-400 px-4 py-3 font-bold text-slate-950" to={`/discuss/${item.discussion_post_id}`} state={{ returnToVideoId: item.video_id }}>Discuss</Link>}
  </div>;
}

function DevelopmentEmbedCard({ item, active, embed }: { item: Video; active: boolean; embed: DevelopmentEmbed }) {
  const [consented, setConsented] = useState(false);
  const playerLoaded = active && consented;
  return <article data-video-id={item.video_id} className="min-h-screen snap-start bg-[#070b14] text-white" aria-label={`${item.creator_label}. ${item.caption}`}>
    <div className="mx-auto flex min-h-screen max-w-5xl flex-col px-4 py-6 sm:px-8">
      <div className="relative grid min-h-[240px] flex-1 place-content-center overflow-hidden rounded-2xl border border-white/15 bg-[#111827] text-center sm:min-h-[360px]">
        {playerLoaded ? <iframe
          className="absolute inset-0 h-full w-full"
          src={`https://www.youtube-nocookie.com/embed/${embed.providerVideoId}?autoplay=0&playsinline=1&rel=0`}
          title={`${item.caption} — ${embed.sourceLabel}`}
          referrerPolicy="strict-origin-when-cross-origin"
          allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          allowFullScreen
        /> : <div className="max-w-2xl p-8">
          <p className="text-sm font-bold uppercase tracking-widest text-amber-300">Development-only official embed test</p>
          <h2 className="mt-3 text-2xl font-bold">Load video from {embed.sourceLabel}</h2>
          <p className="mt-3 leading-7 text-slate-300">The official YouTube player is not loaded until you choose to continue. Loading it shares basic request and playback data with YouTube under its policies.</p>
          {active && <button className="mt-6 rounded-full bg-white px-5 py-3 font-bold text-slate-950" onClick={() => setConsented(true)}>Load official video</button>}
          {!active && consented && <p className="mt-4 text-slate-400">The player was unloaded because this card is not active.</p>}
          <a className="mt-4 block font-semibold text-amber-300 underline" href={embed.canonicalUrl} target="_blank" rel="noreferrer">Watch at the official source instead</a>
        </div>}
      </div>
      <div className="py-6">
        <p className="text-sm font-bold uppercase tracking-widest text-amber-300">Development Watch fixture · {item.issue.title}</p>
        <h1 className="mt-3 text-2xl font-bold sm:text-4xl">{item.caption}</h1>
        {item.transcript && <details className="mt-4 rounded-xl bg-white/10 p-4" open><summary className="cursor-pointer font-semibold">Transcript</summary><p className="mt-2 leading-7 text-slate-100">{item.transcript}</p></details>}
        <CivicActions item={item} />
      </div>
    </div>
  </article>;
}

function NativeVideoCard({ item, active, reducedMotion, onActive }: { item: Video; active: boolean; reducedMotion: boolean; onActive: () => void }) {
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
    {!unavailable ? <video ref={video} className="absolute inset-0 h-full w-full object-cover" src={item.media_url} muted={muted} loop playsInline preload={active ? 'auto' : 'metadata'} onError={() => setUnavailable(true)} onClick={onActive} /> :
      <div className="absolute inset-0 grid place-content-center p-8 text-center" role="alert"><h2 className="text-2xl font-bold">Video unavailable</h2><p className="mt-2 text-slate-300">The transcript and official evidence remain available.</p></div>}
    <div className="absolute inset-0 bg-gradient-to-t from-black via-black/25 to-black/10" />
    <div className="absolute inset-x-0 bottom-0 mx-auto max-w-4xl p-6 pb-12 sm:p-10">
      <p className="text-sm font-bold uppercase tracking-widest text-amber-300">Development Watch fixture · {item.issue.title}</p>
      <h1 className="mt-3 text-2xl font-bold sm:text-4xl">{item.caption}</h1>
      {item.transcript && <details className="mt-4 rounded-xl bg-black/70 p-4" open><summary className="cursor-pointer font-semibold">Transcript</summary><p className="mt-2 leading-7 text-slate-100">{item.transcript}</p></details>}
      <div className="mt-5 flex flex-wrap gap-3">
        <button className="rounded-full bg-white px-4 py-3 font-bold text-slate-950" onClick={() => { onActive(); setManualPause((v) => !v); }}>{active && !manualPause ? <Pause className="inline h-4 w-4" /> : <Play className="inline h-4 w-4" />} <span className="ml-1">{active && !manualPause ? 'Pause' : 'Play'}</span></button>
        <button className="rounded-full bg-white px-4 py-3 font-bold text-slate-950" onClick={() => setMuted((v) => !v)}>{muted ? <VolumeX className="inline h-4 w-4" /> : <Volume2 className="inline h-4 w-4" />} <span className="ml-1">{muted ? 'Unmute' : 'Mute'}</span></button>
        <CivicActions item={item} />
      </div>
    </div>
  </article>;
}

function VideoCard(props: { item: Video; active: boolean; reducedMotion: boolean; onActive: () => void }) {
  const developmentEmbed = DEVELOPMENT_EMBEDS[props.item.video_id];
  return developmentEmbed
    ? <DevelopmentEmbedCard item={props.item} active={props.active} embed={developmentEmbed} />
    : <NativeVideoCard {...props} />;
}

export default function WatchVideoPage() {
  const { videoId } = useParams();
  const navigate = useNavigate();
  const [videos, setVideos] = useState<Video[]>([]);
  const [activeId, setActiveId] = useState(videoId || '');
  const [error, setError] = useState('');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  useEffect(() => {
    const controller = new AbortController();
    fetch(`${getApiBaseUrl()}/videos?limit=25`, { signal: controller.signal }).then(async (r) => { if (!r.ok) throw new Error('Watch could not load'); return r.json() as Promise<Feed>; }).then((feed) => { setVideos(feed.videos); setActiveId((id) => id || feed.videos[0]?.video_id || ''); }).catch((e) => { if (e.name !== 'AbortError') setError(e.message); });
    return () => controller.abort();
  }, []);
  useEffect(() => {
    if (!videos.length) return;
    const observer = new IntersectionObserver((entries) => { const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0]; if (visible) { const id = (visible.target as HTMLElement).dataset.videoId || ''; setActiveId(id); navigate(`/watch/${id}`, { replace: true }); } }, { threshold: [0.6] });
    document.querySelectorAll('[data-video-id]').forEach((node) => observer.observe(node));
    const requested = document.querySelector(`[data-video-id="${CSS.escape(videoId || '')}"]`); requested?.scrollIntoView();
    return () => observer.disconnect();
  }, [videos, videoId, navigate]);
  if (error) return <main className="min-h-screen bg-[#070b14] p-12 text-white" role="alert"><h1 className="text-3xl font-bold">{error}</h1></main>;
  if (!videos.length) return <main className="min-h-screen bg-[#070b14] p-12 text-center text-white">Loading Watch…</main>;
  return <main className="h-screen snap-y snap-mandatory overflow-y-auto bg-[#070b14]">{videos.map((item) => <VideoCard key={item.video_id} item={item} active={activeId === item.video_id} reducedMotion={reducedMotion} onActive={() => setActiveId(item.video_id)} />)}</main>;
}
