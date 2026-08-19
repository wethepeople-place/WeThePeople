import { useEffect, useState, type FormEvent } from 'react';
import { ArrowUpRight, ChevronDown, ChevronUp, MessageCircle, Send, X } from 'lucide-react';
import { Link } from 'react-router-dom';

import {
  createDiscussionReply,
  createVideoComment,
  fetchPublicDiscussion,
  fetchVideoComments,
  type PublicDiscussionDetail,
  type PublicDiscussionPost,
} from '../api/civic';
import { useAuth } from '../contexts/AuthContext';

type Props = {
  videoId: string;
  videoCaption: string;
  open: boolean;
  onClose: () => void;
};

function ReplyThread({ post, onReplyCreated }: { post: PublicDiscussionPost; onReplyCreated: () => void }) {
  const { isAuthenticated } = useAuth();
  const [expanded, setExpanded] = useState(false);
  const [detail, setDetail] = useState<PublicDiscussionDetail | null>(null);
  const [body, setBody] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const toggle = async () => {
    if (expanded) { setExpanded(false); return; }
    setExpanded(true);
    if (detail || post.reply_count === 0) return;
    try { setDetail(await fetchPublicDiscussion(post.id)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Replies could not load.'); }
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true); setError('');
    try {
      await createDiscussionReply(post.id, body);
      setBody('');
      setDetail(await fetchPublicDiscussion(post.id));
      setExpanded(true);
      onReplyCreated();
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Reply could not be posted.'); }
    finally { setSubmitting(false); }
  };

  return <article className="border-b border-white/10 px-5 py-5">
    <div className="flex gap-3">
      <div aria-hidden="true" className="grid h-9 w-9 shrink-0 place-content-center rounded-full bg-amber-300 font-bold text-slate-950">{post.author.display_name.slice(0, 1).toUpperCase()}</div>
      <div className="min-w-0 flex-1">
        <p className="font-semibold text-white">{post.author.display_name}</p>
        <p className="mt-1 whitespace-pre-wrap leading-6 text-slate-200">{post.body}</p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button type="button" className="inline-flex min-h-11 items-center gap-2 rounded-full px-2 text-sm font-semibold text-slate-300 outline-none hover:text-white focus-visible:ring-4 focus-visible:ring-amber-300/70" aria-expanded={expanded} onClick={() => void toggle()}>
            {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            {post.reply_count ? `${post.reply_count} ${post.reply_count === 1 ? 'reply' : 'replies'}` : 'Reply'}
          </button>
          <Link className="inline-flex min-h-11 items-center rounded-full px-2 text-sm font-semibold text-amber-300 outline-none hover:text-amber-200 focus-visible:ring-4 focus-visible:ring-amber-300/70" to={`/discuss/${post.id}`}>Open full discussion</Link>
        </div>
      </div>
    </div>
    {expanded && <div className="ml-12 mt-3 space-y-3">
      {detail?.replies.map((reply) => <div key={reply.id} className="rounded-2xl bg-white/5 px-4 py-3"><p className="text-sm font-semibold text-white">{reply.author.display_name}</p><p className="mt-1 whitespace-pre-wrap text-sm leading-6 text-slate-200">{reply.body}</p></div>)}
      {post.reply_count > 0 && !detail && !error && <p className="text-sm text-slate-400">Loading replies…</p>}
      {isAuthenticated ? <form className="flex items-end gap-2" onSubmit={submit}>
        <label className="sr-only" htmlFor={`reply-${post.id}`}>Reply to {post.author.display_name}</label>
        <textarea id={`reply-${post.id}`} required maxLength={10000} rows={2} value={body} onChange={(event) => setBody(event.target.value)} className="min-h-12 flex-1 resize-none rounded-2xl border border-white/15 bg-black/30 px-4 py-3 text-sm text-white outline-none placeholder:text-slate-500 focus-visible:ring-4 focus-visible:ring-amber-300/70" placeholder="Write a reply…" />
        <button disabled={submitting} className="grid min-h-12 min-w-12 place-content-center rounded-full bg-amber-300 text-slate-950 outline-none focus-visible:ring-4 focus-visible:ring-white/70 disabled:opacity-60" aria-label="Post reply"><Send className="h-5 w-5" /></button>
      </form> : <Link className="inline-block py-2 text-sm font-semibold text-amber-300 underline" to={`/login?next=${encodeURIComponent(`/discuss/${post.id}`)}`}>Sign in to reply</Link>}
      {error && <p role="alert" className="text-sm text-rose-300">{error}</p>}
    </div>}
  </article>;
}

export default function VideoCommentsPanel({ videoId, videoCaption, open, onClose }: Props) {
  const { isAuthenticated } = useAuth();
  const [items, setItems] = useState<PublicDiscussionPost[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [body, setBody] = useState('');
  const [notice, setNotice] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const load = async () => {
    setLoading(true); setError('');
    try { setItems((await fetchVideoComments(videoId)).items); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Comments could not load.'); }
    finally { setLoading(false); }
  };

  useEffect(() => { if (open) void load(); }, [open, videoId]);
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  const submit = async (event: FormEvent) => {
    event.preventDefault(); setSubmitting(true); setError(''); setNotice('');
    try {
      const result = await createVideoComment(videoId, body);
      setBody('');
      setNotice(`${result.message}. It will appear after review.`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Comment could not be submitted.'); }
    finally { setSubmitting(false); }
  };

  if (!open) return null;
  return <div className="fixed inset-0 z-50 flex items-end justify-end bg-black/70 md:items-stretch" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <aside aria-label={`Comments for ${videoCaption}`} aria-modal="true" role="dialog" className="flex h-[86vh] w-full flex-col overflow-hidden rounded-t-3xl border-l border-white/10 bg-[#090d16] text-white shadow-2xl md:h-full md:max-w-md md:rounded-none">
      <header className="flex items-center justify-between border-b border-white/10 px-5 py-4">
        <div><h2 className="text-xl font-bold">Comments <span className="text-slate-400">{items.reduce((sum, item) => sum + 1 + item.reply_count, 0)}</span></h2><p className="mt-1 line-clamp-1 text-xs text-slate-400">{videoCaption}</p></div>
        <button autoFocus type="button" onClick={onClose} className="grid min-h-11 min-w-11 place-content-center rounded-full bg-white/10 outline-none hover:bg-white/15 focus-visible:ring-4 focus-visible:ring-amber-300/70" aria-label="Close comments"><X className="h-5 w-5" /></button>
      </header>
      <Link className="flex min-h-11 items-center justify-between border-b border-white/10 bg-white/[0.03] px-5 text-sm font-semibold text-amber-300 outline-none hover:bg-white/[0.06] hover:text-amber-200 focus-visible:ring-4 focus-visible:ring-inset focus-visible:ring-amber-300/70" to={`/discuss?video=${encodeURIComponent(videoId)}`}>
        View this video's full conversation
        <ArrowUpRight className="h-4 w-4" />
      </Link>
      <div className="flex-1 overflow-y-auto overscroll-contain">
        {loading && <p className="p-6 text-slate-400">Loading comments…</p>}
        {error && <p role="alert" className="m-5 rounded-2xl border border-rose-400/30 bg-rose-400/10 p-4 text-rose-200">{error}</p>}
        {!loading && !error && items.length === 0 && <div className="grid min-h-64 place-content-center px-8 text-center"><MessageCircle className="mx-auto h-9 w-9 text-slate-500" /><h3 className="mt-4 text-lg font-semibold">No published comments yet</h3><p className="mt-2 text-sm leading-6 text-slate-400">Start a sourced, civil conversation. Nothing is posted automatically.</p></div>}
        {!loading && items.map((post) => <ReplyThread key={post.id} post={post} onReplyCreated={() => void load()} />)}
      </div>
      <footer className="border-t border-white/10 bg-[#090d16] p-4">
        {isAuthenticated ? <form onSubmit={submit} className="flex items-end gap-2">
          <label className="sr-only" htmlFor={`video-comment-${videoId}`}>Add a comment</label>
          <textarea id={`video-comment-${videoId}`} required maxLength={10000} rows={2} value={body} onChange={(event) => setBody(event.target.value)} className="min-h-12 flex-1 resize-none rounded-2xl border border-white/15 bg-white/5 px-4 py-3 text-white outline-none placeholder:text-slate-500 focus-visible:ring-4 focus-visible:ring-amber-300/70" placeholder="Add a comment…" />
          <button disabled={submitting} className="grid min-h-12 min-w-12 place-content-center rounded-full bg-amber-300 text-slate-950 outline-none focus-visible:ring-4 focus-visible:ring-white/70 disabled:opacity-60" aria-label="Submit comment for review"><Send className="h-5 w-5" /></button>
        </form> : <Link className="block rounded-full bg-amber-300 px-5 py-3 text-center font-bold text-slate-950 outline-none focus-visible:ring-4 focus-visible:ring-white/70" to={`/login?next=${encodeURIComponent(`/watch/${videoId}?comments=1`)}`}>Sign in to comment</Link>}
        {notice && <p role="status" className="mt-2 text-sm text-amber-200">{notice}</p>}
      </footer>
    </aside>
  </div>;
}
