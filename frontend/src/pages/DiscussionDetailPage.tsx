import { useEffect, useState, type FormEvent } from 'react';
import { Image as ImageIcon, Lightbulb, Link2, MessageCircle, Send, Video } from 'lucide-react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { createDiscussionReply, fetchPublicDiscussion, PublicDiscussionDetail } from '../api/civic';
import DiscussionVideoEmbed from '../components/DiscussionVideoEmbed';
import { useAuth } from '../contexts/AuthContext';

export default function DiscussionDetailPage() {
  const { postId = '' } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [item, setItem] = useState<PublicDiscussionDetail | null>(null);
  const [error, setError] = useState('');
  const [replyBody, setReplyBody] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [notice, setNotice] = useState('');
  const [replyError, setReplyError] = useState('');
  const { isAuthenticated } = useAuth();
  useEffect(() => { fetchPublicDiscussion(Number(postId)).then(setItem).catch((reason) => setError(reason.message)); }, [postId]);
  if (error) return <main className="min-h-screen bg-bg p-12 text-text-1"><div role="alert">{error}</div></main>;
  if (!item) return <main className="min-h-screen bg-bg p-16 text-center text-text-2">Loading discussion…</main>;

  const issue = item.attachments.find((value) => value.type === 'issue');
  const solution = item.attachments.find((value) => value.type === 'solution');
  const related = item.attachments.filter((value) => ['video', 'bill', 'politician', 'source'].includes(value.type));
  const href = (type: string, id: string) => ({
    video: `/discuss?video=${encodeURIComponent(id)}`,
    bill: `/politics/bill/${id}`,
    politician: `/politics/people/${id}`,
  }[type]);
  const issueQuery = issue ? `issue=${encodeURIComponent(issue.reference_id)}&` : '';
  const submitReply = async (event: FormEvent) => {
    event.preventDefault();
    const body = replyBody.trim();
    if (!body) return;
    setSubmitting(true); setReplyError(''); setNotice('');
    try {
      await createDiscussionReply(item.id, body);
      setReplyBody('');
      if ((location.state as { returnAfterReply?: boolean } | null)?.returnAfterReply) {
        navigate(-1);
        return;
      }
      setItem(await fetchPublicDiscussion(item.id));
      setNotice('Reply posted.');
    } catch (reason) { setReplyError(reason instanceof Error ? reason.message : 'Unable to post reply.'); }
    finally { setSubmitting(false); }
  };

  return <main className="min-h-screen bg-bg px-5 py-12 text-text-1"><div className="mx-auto max-w-3xl">
    <p className="text-xs font-bold uppercase tracking-[0.18em] text-accent-text">Citizen discussion</p>
    {item.author.is_demo && <aside role="note" className="mt-4 rounded-xl border border-amber-500/40 bg-amber-300/10 p-4 text-sm text-text-2"><strong className="text-text-1">Visual demo:</strong> This thread uses Latin placeholder text and numbered test users. It is not real civic participation.</aside>}
    <h1 className="mt-4 font-display text-4xl">{item.body}</h1>
    <p className="mt-3 text-sm text-text-3">{item.author.display_name}</p>
    {item.video_link && <DiscussionVideoEmbed video={item.video_link} title={`Video shared by ${item.author.display_name}`} postId={item.id} />}
    <Link className="mt-4 inline-flex min-h-11 items-center rounded-full border border-amber-300/40 bg-amber-300/10 px-4 font-bold text-amber-300" to={`/act?target_type=discussion&target_id=${item.id}`}>ACT on this conversation</Link>
    {related.length > 0 && <aside aria-label="Related civic context" className="mt-8 flex flex-wrap gap-2">{related.map((attachment) => {
      const internal = href(attachment.type, attachment.reference_id);
      const label = attachment.label || attachment.source?.publisher || `Related ${attachment.type}`;
      if (attachment.type === 'source' && attachment.source) return <a key={`${attachment.type}-${attachment.reference_id}`} className="rounded-pill border border-border px-3 py-2 text-sm text-accent-text" href={attachment.source.url} target="_blank" rel="noreferrer">{label}</a>;
      return internal ? <Link key={`${attachment.type}-${attachment.reference_id}`} className="rounded-pill border border-border px-3 py-2 text-sm text-accent-text" to={internal}>{label}</Link> : null;
    })}</aside>}
    <section className="mt-10" aria-labelledby="conversation-replies"><h2 id="conversation-replies" className="text-2xl font-semibold">Replies <span className="text-text-3">{item.reply_total}</span></h2>
      {item.replies.length ? <div className="mt-4 space-y-3">{item.replies.map((reply) => <article key={reply.id} className="rounded-card border border-border bg-surface p-5"><p className="whitespace-pre-wrap">{reply.body}</p><p className="mt-2 text-xs text-text-3">{reply.author.display_name}</p></article>)}</div> : <p className="mt-3 text-text-2">No replies yet. Be the first to join this conversation.</p>}
    </section>
    <section className="mt-7 rounded-2xl border border-border bg-surface p-4 sm:p-5" aria-label="Join this conversation">
      {isAuthenticated ? <form onSubmit={submitReply} className="space-y-3">
        <label htmlFor="conversation-reply" className="font-semibold">Write a reply</label>
        <textarea id="conversation-reply" required maxLength={10000} rows={3} value={replyBody} onChange={(event) => setReplyBody(event.target.value)} className="w-full resize-y rounded-2xl border border-border bg-bg px-4 py-3 text-text-1 outline-none placeholder:text-text-3 focus-visible:ring-4 focus-visible:ring-accent/30" placeholder="Add your perspective or paste a supporting link…" />
        <div className="flex flex-wrap items-center gap-2"><button disabled={submitting || !replyBody.trim()} className="inline-flex min-h-11 items-center gap-2 rounded-full bg-accent px-5 font-bold text-white disabled:opacity-40"><Send className="h-4 w-4" />{submitting ? 'Posting…' : 'Post reply'}</button><span className="text-xs text-text-3">Text and links are available.</span></div>
      </form> : <Link className="inline-flex min-h-11 items-center gap-2 rounded-full bg-accent px-5 font-bold text-white" to={`/login?next=${encodeURIComponent(`/discuss/${item.id}`)}`}><MessageCircle className="h-4 w-4" />Sign in to reply</Link>}
      {notice && <p role="status" className="mt-3 text-sm text-accent-text">{notice}</p>}
      {replyError && <p role="alert" className="mt-3 text-sm text-red-700">{replyError}</p>}
      <div className="mt-5 border-t border-border pt-4"><p className="text-sm font-semibold">Other ways to contribute</p><div className="mt-3 flex flex-wrap gap-2">
        <Link className="inline-flex min-h-11 items-center gap-2 rounded-full border border-border px-4 text-sm font-bold" to={`/discuss?${issueQuery}compose=1#composer`}><MessageCircle className="h-4 w-4" />Start a discussion</Link>
        {issue && <Link className="inline-flex min-h-11 items-center gap-2 rounded-full border border-border px-4 text-sm font-bold" to={`/discuss?issue=${encodeURIComponent(issue.reference_id)}&compose=proposal#composer`}><Lightbulb className="h-4 w-4" />Propose a solution</Link>}
        <Link className="inline-flex min-h-11 items-center gap-2 rounded-full border border-border px-4 text-sm font-bold" to={`/discuss?${issueQuery}compose=1#composer`}><Link2 className="h-4 w-4" />Share link or video</Link>
        <button type="button" disabled title="Image uploads are coming after safety controls are ready" className="inline-flex min-h-11 items-center gap-2 rounded-full border border-border px-4 text-sm font-bold opacity-45"><ImageIcon className="h-4 w-4" />Image · soon</button>
        <button type="button" disabled title="Native video uploads are coming after safety controls are ready" className="inline-flex min-h-11 items-center gap-2 rounded-full border border-border px-4 text-sm font-bold opacity-45"><Video className="h-4 w-4" />Upload · soon</button>
      </div></div>
    </section>
    <div className="mt-10 flex flex-wrap gap-5">
      {solution && issue && <Link className="text-accent-text underline" to={`/issues/${issue.reference_id}/solutions/${solution.reference_id}`}>Return to solution</Link>}
      {issue ? <Link className="text-accent-text underline" to={`/issues/${issue.reference_id}`}>Official evidence</Link> : <Link className="text-accent-text underline" to="/discuss">All public discussions</Link>}
    </div>
  </div></main>;
}
