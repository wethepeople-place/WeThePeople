import { useCallback, useEffect, useState } from 'react';
import { Bookmark, ExternalLink, Play, Trash2 } from 'lucide-react';
import { Link, Navigate, useLocation } from 'react-router-dom';

import { getApiBaseUrl } from '../api/client';
import { useAuth } from '../contexts/AuthContext';

type SavedVideo = {
  video_id: string;
  creator_label: string;
  caption: string;
  saved: boolean;
  delivery: { poster_url?: string | null; source_label?: string | null } | null;
  issue: { slug: string; title: string };
  source: { url: string; publisher: string };
};

type SavedResponse = { total: number; videos: SavedVideo[]; has_more: boolean };

export default function SavedVideosPage() {
  const location = useLocation();
  const { isAuthenticated, loading: authLoading, authedFetch } = useAuth();
  const [videos, setVideos] = useState<SavedVideo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [removing, setRemoving] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await authedFetch(`${getApiBaseUrl()}/videos/saved`, { cache: 'no-store' });
      if (!response.ok) throw new Error('Your saved videos could not be loaded. Please try again.');
      const data = await response.json() as SavedResponse;
      setVideos(data.videos);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Your saved videos could not be loaded.');
    } finally {
      setLoading(false);
    }
  }, [authedFetch]);

  useEffect(() => { if (isAuthenticated) void load(); }, [isAuthenticated, load]);

  const remove = async (video: SavedVideo) => {
    setRemoving(video.video_id);
    setError('');
    try {
      const response = await authedFetch(`${getApiBaseUrl()}/videos/${encodeURIComponent(video.video_id)}/save`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active: false }),
      });
      if (!response.ok) throw new Error('This video could not be removed. Please try again.');
      setVideos((current) => current.filter((item) => item.video_id !== video.video_id));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'This video could not be removed.');
    } finally {
      setRemoving('');
    }
  };

  if (authLoading) return <main className="min-h-screen bg-[#070b14] px-4 py-24 text-center text-white">Loading your account…</main>;
  if (!isAuthenticated) return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />;

  return <main className="min-h-screen bg-[#070b14] px-4 py-20 text-white sm:px-8">
    <div className="mx-auto max-w-6xl">
      <p className="text-sm font-bold uppercase tracking-[0.2em] text-amber-300">Private collection</p>
      <h1 className="mt-2 text-4xl font-bold sm:text-5xl">Saved videos</h1>
      <p className="mt-3 max-w-2xl text-slate-300">Only you can see this collection. Open any video to return to its evidence, issue, bill, and discussion context.</p>

      {error && <div className="mt-8 rounded-xl border border-rose-400/50 bg-rose-950/40 p-4" role="alert"><p>{error}</p><button className="mt-3 rounded-full bg-white px-4 py-2 font-bold text-slate-950 outline-none focus-visible:ring-4 focus-visible:ring-amber-300/70" onClick={() => void load()}>Try again</button></div>}
      {loading && <p className="mt-12 text-slate-300" role="status">Loading saved videos…</p>}
      {!loading && !error && videos.length === 0 && <section className="mt-10 rounded-2xl border border-white/15 bg-white/5 p-8 text-center">
        <Bookmark className="mx-auto h-10 w-10 text-amber-300" aria-hidden="true" />
        <h2 className="mt-4 text-2xl font-bold">No saved videos yet</h2>
        <p className="mx-auto mt-2 max-w-lg text-slate-300">Use the Save control on a Watch video to keep it here privately.</p>
        <Link className="mt-6 inline-flex min-h-11 items-center rounded-full bg-amber-300 px-5 py-3 font-bold text-slate-950 outline-none focus-visible:ring-4 focus-visible:ring-white/70" to="/watch">Explore Watch</Link>
      </section>}
      {!loading && videos.length > 0 && <ul className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3" aria-label="Your saved videos">
        {videos.map((video) => <li key={video.video_id} className="min-w-0 overflow-hidden rounded-2xl border border-white/15 bg-slate-900">
          <Link className="group block outline-none focus-visible:ring-4 focus-visible:ring-inset focus-visible:ring-amber-300/70" to={`/videos/${video.video_id}`}>
            <div className="relative aspect-video bg-gradient-to-br from-slate-700 to-slate-950">
              {video.delivery?.poster_url && <img className="h-full w-full object-cover" src={video.delivery.poster_url} alt="" />}
              <div className="absolute inset-0 bg-black/35 transition group-hover:bg-black/20" />
              <span className="absolute inset-0 grid place-content-center"><span className="grid h-14 w-14 place-content-center rounded-full bg-white text-slate-950"><Play className="ml-1 h-6 w-6 fill-current" aria-hidden="true" /></span></span>
            </div>
            <div className="p-5">
              <p className="text-xs font-bold uppercase tracking-widest text-amber-300">{video.issue.title}</p>
              <h2 className="mt-2 text-xl font-bold leading-snug">{video.caption}</h2>
              <p className="mt-2 text-sm text-slate-400">{video.creator_label}</p>
            </div>
          </Link>
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-white/10 px-5 py-3">
            <a className="min-h-11 py-3 text-sm font-semibold text-slate-300 underline outline-none focus-visible:ring-4 focus-visible:ring-amber-300/70" href={video.source.url} target="_blank" rel="noreferrer">Official source <ExternalLink className="inline h-4 w-4" /></a>
            <button className="inline-flex min-h-11 items-center gap-2 rounded-full px-3 py-2 text-sm font-bold text-slate-300 outline-none hover:bg-white/10 focus-visible:ring-4 focus-visible:ring-amber-300/70 disabled:opacity-60" disabled={removing === video.video_id} onClick={() => void remove(video)} aria-label={`Remove ${video.caption} from saved videos`}><Trash2 className="h-4 w-4" aria-hidden="true" />{removing === video.video_id ? 'Removing…' : 'Remove'}</button>
          </div>
        </li>)}
      </ul>}
    </div>
  </main>;
}
