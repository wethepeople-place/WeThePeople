import { useEffect, useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { createVideoDiscussion, fetchPublicDiscussions, type PublicDiscussionPost } from '../api/civic';
import DiscussionVideoEmbed from '../components/DiscussionVideoEmbed';
import { useAuth } from '../contexts/AuthContext';

function attachmentUrl(attachment: PublicDiscussionPost['attachments'][number]): string | null {
  switch (attachment.type) {
    case 'video': return `/watch/${attachment.reference_id}`;
    case 'issue': return `/issues/${attachment.reference_id}`;
    case 'bill': return `/politics/bill/${attachment.reference_id}`;
    case 'politician': return `/politics/people/${attachment.reference_id}`;
    case 'solution': return `/issues/housing-rent/solutions/${attachment.reference_id}`;
    default: return null;
  }
}

export default function DiscussionsPage() {
  const [params] = useSearchParams();
  const issue = params.get('issue') || '';
  const [items, setItems] = useState<PublicDiscussionPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [body, setBody] = useState('');
  const [videoUrl, setVideoUrl] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [notice, setNotice] = useState('');
  const { isAuthenticated } = useAuth();

  useEffect(() => {
    let active = true;
    fetchPublicDiscussions(issue || undefined).then((result) => active && setItems(result.items)).catch((reason) => active && setError(reason.message)).finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [issue]);

  const submit = async (event: FormEvent) => {
    event.preventDefault(); setError(''); setNotice(''); setSubmitting(true);
    try {
      const result = await createVideoDiscussion({ body, video_url: videoUrl, ...(issue ? { issue_slug: issue } : {}) });
      setBody(''); setVideoUrl(''); setNotice(`${result.message}. It will appear here after review.`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to submit post'); }
    finally { setSubmitting(false); }
  };

  return <main className="min-h-screen bg-bg px-5 py-12 text-text-1"><div className="mx-auto max-w-3xl">
    <p className="text-xs font-bold uppercase tracking-[0.18em] text-accent-text">Discuss</p>
    <h1 className="mt-3 font-display text-4xl sm:text-5xl">Public civic discussion</h1>
    <p className="mt-3 max-w-2xl text-text-2">{issue ? 'Conversation connected to this issue’s reviewed evidence, government activity, and citizen solutions.' : 'Conversation connected to reviewed evidence, government activity, and citizen solutions.'}</p>
    {issue && <p className="mt-4"><Link className="text-accent-text underline" to={`/issues/${issue}`}>Return to official issue evidence</Link></p>}

    <section className="mt-8 rounded-card border border-border bg-surface p-6" aria-labelledby="share-video-heading">
      <h2 id="share-video-heading" className="text-xl font-semibold">Share a YouTube video</h2>
      <p className="mt-2 text-sm text-text-2">Paste the link and add why it matters. New posts are reviewed before appearing publicly.</p>
      {isAuthenticated ? <form className="mt-5 space-y-4" onSubmit={submit}>
        <label className="block text-sm font-semibold">YouTube link<input className="mt-2 w-full rounded-xl border border-border bg-bg px-4 py-3 text-text-1" type="url" required placeholder="https://www.youtube.com/watch?v=..." value={videoUrl} onChange={(event) => setVideoUrl(event.target.value)} /></label>
        <label className="block text-sm font-semibold">Your comment<textarea className="mt-2 min-h-28 w-full rounded-xl border border-border bg-bg px-4 py-3 text-text-1" required maxLength={10000} placeholder="What should people notice, question, or discuss?" value={body} onChange={(event) => setBody(event.target.value)} /></label>
        <button disabled={submitting} className="rounded-full bg-accent px-5 py-3 font-bold text-white disabled:opacity-60">{submitting ? 'Submitting…' : 'Submit for review'}</button>
      </form> : <p className="mt-4"><Link className="text-accent-text underline" to="/login">Sign in to make a post</Link></p>}
      {notice && <p role="status" className="mt-4 text-sm text-accent-text">{notice}</p>}
    </section>

    {loading && <p className="mt-10 text-text-2">Loading discussions…</p>}
    {error && <div role="alert" className="mt-6 rounded-card border border-border bg-surface p-6 text-text-2">{error}</div>}
    {!loading && !error && items.length === 0 && <div className="mt-10 rounded-card border border-border bg-surface p-8"><h2 className="text-xl font-semibold">No published discussions yet</h2><p className="mt-2 text-text-2">Reviewed, source-linked conversations will appear here.</p><Link className="mt-5 inline-block text-accent-text underline" to="/watch">Explore Watch</Link></div>}

    <section className="mt-10 space-y-5">{items.map((item) => <article key={item.id} className="rounded-card border border-border bg-surface p-6">
      <Link className="block text-lg leading-8 hover:text-accent-text" to={`/discuss/${item.id}`}>{item.body}</Link>
      <p className="mt-3 text-sm text-text-3">{item.author.display_name} · {item.reply_count} {item.reply_count === 1 ? 'reply' : 'replies'}</p>
      {item.video_link && <DiscussionVideoEmbed video={item.video_link} title={`YouTube video shared by ${item.author.display_name}`} />}
      {item.attachments.length > 0 && <div className="mt-4 flex flex-wrap gap-2">{item.attachments.map((attachment) => {
        const url = attachmentUrl(attachment); const label = attachment.label || `${attachment.type}: ${attachment.reference_id}`;
        return url ? <Link key={`${attachment.type}-${attachment.reference_id}`} className="rounded-pill border border-accent/40 px-3 py-1 text-sm text-accent-text" to={url}>{label}</Link> : <span key={`${attachment.type}-${attachment.reference_id}`} className="rounded-pill border border-border px-3 py-1 text-sm text-text-2">{label}</span>;
      })}</div>}
    </article>)}</section>
  </div></main>;
}
