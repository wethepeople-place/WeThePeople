import { useEffect, useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { createVideoDiscussion, fetchPublicDiscussions, type PublicDiscussionPost } from '../api/civic';
import DiscussionPostCard from '../components/DiscussionPostCard';
import { useAuth } from '../contexts/AuthContext';

const PAGE_SIZE = 20;

export default function DiscussionsPage() {
  const [params] = useSearchParams();
  const issue = params.get('issue') || '';
  const videoId = params.get('video') || '';
  const [items, setItems] = useState<PublicDiscussionPost[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState('');
  const [body, setBody] = useState('');
  const [videoUrl, setVideoUrl] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [notice, setNotice] = useState('');
  const { isAuthenticated } = useAuth();

  useEffect(() => {
    let active = true;
    setLoading(true); setError(''); setItems([]);
    fetchPublicDiscussions(issue || undefined, videoId || undefined, 0, PAGE_SIZE)
      .then((result) => { if (active) { setItems(result.items); setTotal(result.total); } })
      .catch((reason) => active && setError(reason instanceof Error ? reason.message : 'Discussions could not load.'))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [issue, videoId]);

  const loadMore = async () => {
    setLoadingMore(true); setError('');
    try {
      const result = await fetchPublicDiscussions(issue || undefined, videoId || undefined, items.length, PAGE_SIZE);
      setItems((current) => [...current, ...result.items]); setTotal(result.total);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'More discussions could not load.'); }
    finally { setLoadingMore(false); }
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault(); setError(''); setNotice(''); setSubmitting(true);
    try {
      const result = await createVideoDiscussion({ body, video_url: videoUrl, ...(issue ? { issue_slug: issue } : {}) });
      setBody(''); setVideoUrl(''); setNotice(`${result.message}. It will appear here after review.`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to submit post.'); }
    finally { setSubmitting(false); }
  };

  return <main className="min-h-screen bg-bg px-4 py-8 text-text-1 sm:px-6 sm:py-12">
    <div className="mx-auto max-w-6xl">
      <header className="border-b border-border pb-6">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-accent-text">Civic Conversation Loop</p>
        <h1 className="mt-2 font-display text-4xl sm:text-5xl">Discuss</h1>
        <p className="mt-3 max-w-3xl text-lg leading-7 text-text-2">A chronological public feed connected to evidence, legislation, representatives, solutions, and reviewed videos—not an outrage-ranked timeline.</p>
        <nav aria-label="Discussion feed views" className="mt-6 flex gap-2"><span aria-current="page" className="rounded-full bg-accent px-5 py-2.5 text-sm font-bold text-white">Latest</span><span className="rounded-full border border-border px-5 py-2.5 text-sm text-text-3" title="Following will be enabled after its privacy and notification contracts are complete">Following — later</span></nav>
        {videoId && <div className="mt-5 rounded-xl border border-accent/30 bg-accent/5 p-4"><p className="text-sm text-text-2">Showing the published conversation attached to this exact reviewed video.</p><Link className="mt-2 inline-block font-semibold text-accent-text underline" to={`/watch/${videoId}?comments=1`}>Return to Watch with comments open</Link></div>}
        {issue && <div className="mt-5 rounded-xl border border-accent/30 bg-accent/5 p-4"><p className="text-sm text-text-2">Showing conversation connected to this issue's reviewed civic record.</p><Link className="mt-2 inline-block font-semibold text-accent-text underline" to={`/issues/${issue}`}>Return to official issue evidence</Link></div>}
      </header>

      <div className="mt-7 grid items-start gap-7 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <div className="min-w-0">
          <section className="rounded-2xl border border-border bg-surface p-5 sm:p-6" aria-labelledby="share-video-heading">
            <h2 id="share-video-heading" className="text-xl font-semibold">Start a sourced conversation</h2>
            <p className="mt-2 text-sm leading-6 text-text-2">Share a YouTube link and explain why it matters. New posts are reviewed before appearing publicly.</p>
            {isAuthenticated ? <form className="mt-5 space-y-4" onSubmit={submit}>
              <label className="block text-sm font-semibold">YouTube link<input className="mt-2 min-h-11 w-full rounded-xl border border-border bg-bg px-4 py-3 text-text-1" type="url" required placeholder="https://www.youtube.com/watch?v=..." value={videoUrl} onChange={(event) => setVideoUrl(event.target.value)} /></label>
              <label className="block text-sm font-semibold">What should people examine?<textarea className="mt-2 min-h-28 w-full rounded-xl border border-border bg-bg px-4 py-3 text-text-1" required maxLength={10000} placeholder="Point to evidence, ask a focused question, or explain the civic tradeoff." value={body} onChange={(event) => setBody(event.target.value)} /></label>
              <button disabled={submitting} className="min-h-11 rounded-full bg-accent px-5 py-3 font-bold text-white disabled:opacity-60">{submitting ? 'Submitting…' : 'Submit for review'}</button>
            </form> : <p className="mt-4"><Link className="font-semibold text-accent-text underline" to={`/login?next=${encodeURIComponent('/discuss')}`}>Sign in to start a conversation</Link></p>}
            {notice && <p role="status" className="mt-4 text-sm text-accent-text">{notice}</p>}
          </section>

          {loading && <div className="mt-6 space-y-4" aria-label="Loading latest discussions"><div className="h-56 animate-pulse rounded-2xl border border-border bg-surface" /><div className="h-56 animate-pulse rounded-2xl border border-border bg-surface" /></div>}
          {error && <div role="alert" className="mt-6 rounded-2xl border border-red-300 bg-red-50 p-5 text-red-800">{error}<button type="button" onClick={() => window.location.reload()} className="ml-3 font-bold underline">Try again</button></div>}
          {!loading && !error && items.length === 0 && <div className="mt-6 rounded-2xl border border-dashed border-border bg-surface p-8 text-center"><h2 className="text-xl font-semibold">No published discussions yet</h2><p className="mt-2 text-text-2">{videoId ? 'No reviewed conversation is connected to this video yet. Nothing is created or published automatically.' : 'Reviewed, source-linked conversations will appear here in newest-first order.'}</p><Link className="mt-5 inline-block font-semibold text-accent-text underline" to={videoId ? `/watch/${videoId}` : '/watch'}>{videoId ? 'Return to this video' : 'Explore Watch'}</Link></div>}

          <section aria-label="Latest civic discussions" className="mt-6 space-y-5">{items.map((item) => <DiscussionPostCard key={item.id} item={item} isAuthenticated={isAuthenticated} />)}</section>
          {items.length < total && <div className="mt-6 text-center"><button type="button" disabled={loadingMore} onClick={() => void loadMore()} className="min-h-11 rounded-full border border-border bg-surface px-6 font-bold text-text-1 disabled:opacity-60">{loadingMore ? 'Loading…' : `Load more (${total - items.length} remaining)`}</button></div>}
        </div>

        <aside className="rounded-2xl border border-border bg-surface p-5 lg:sticky lg:top-6" aria-label="About this feed"><h2 className="font-semibold">How this feed works</h2><ul className="mt-3 space-y-3 text-sm leading-6 text-text-2"><li>Newest published conversations appear first.</li><li>Civic labels link back to the underlying evidence or public record.</li><li>Bookmarks are private. Reactions show totals, never participant lists.</li><li>Reports go privately to moderation.</li><li>Video playback requires provider consent.</li></ul><Link className="mt-5 inline-block font-semibold text-accent-text underline" to="/watch">Explore reviewed videos</Link></aside>
      </div>
    </div>
  </main>;
}
