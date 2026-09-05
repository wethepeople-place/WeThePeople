import { useEffect, useState, type FormEvent } from 'react';
import { ArrowLeft, Send } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';

import { createDiscussionReply, fetchPublicDiscussion, type PublicDiscussionDetail } from '../api/civic';

export default function DiscussionReplyPage() {
  const { postId = '' } = useParams();
  const navigate = useNavigate();
  const [post, setPost] = useState<PublicDiscussionDetail | null>(null);
  const [body, setBody] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => { fetchPublicDiscussion(Number(postId)).then(setPost).catch((reason) => setError(reason.message)); }, [postId]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true); setError('');
    try {
      await createDiscussionReply(Number(postId), body.trim());
      navigate(-1);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Reply could not be posted.'); }
    finally { setSubmitting(false); }
  };

  return <main className="min-h-screen bg-bg px-5 py-6 text-text-1"><div className="mx-auto max-w-2xl">
    <header className="flex items-center justify-between"><button type="button" onClick={() => navigate(-1)} className="inline-flex min-h-11 items-center gap-2 text-text-2"><ArrowLeft className="h-5 w-5" />Cancel</button><button form="quick-reply" disabled={submitting || !body.trim()} className="min-h-11 rounded-full bg-accent px-6 font-bold text-white disabled:opacity-40">{submitting ? 'Posting…' : 'Post'}</button></header>
    {post && <article className="mt-8 border-l-2 border-border pl-5"><p className="font-bold">{post.author.display_name}</p><p className="mt-2 whitespace-pre-wrap text-lg leading-7">{post.body}</p><p className="mt-5 text-sm text-text-3">Replying to {post.author.display_name}</p></article>}
    <form id="quick-reply" onSubmit={submit} className="mt-5 flex gap-3"><div aria-hidden="true" className="grid h-10 w-10 shrink-0 place-content-center rounded-full bg-accent/15 font-bold text-accent-text">You</div><label className="sr-only" htmlFor="quick-reply-body">Post your reply</label><textarea autoFocus id="quick-reply-body" required maxLength={10000} rows={7} value={body} onChange={(event) => setBody(event.target.value)} className="min-h-48 flex-1 resize-none bg-transparent text-xl leading-8 outline-none placeholder:text-text-3" placeholder="Post your reply" /></form>
    {error && <p role="alert" className="mt-4 text-red-600">{error}</p>}
    <div className="mt-6 flex items-center gap-2 border-t border-border pt-4 text-sm text-text-3"><Send className="h-4 w-4" />Text and supporting links are available.</div>
  </div></main>;
}
