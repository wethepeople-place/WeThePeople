import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { fetchPublicDiscussion, PublicDiscussionDetail } from '../api/civic';

export default function DiscussionDetailPage() {
  const { postId = '' } = useParams();
  const [item, setItem] = useState<PublicDiscussionDetail | null>(null);
  const [error, setError] = useState('');
  useEffect(() => { fetchPublicDiscussion(Number(postId)).then(setItem).catch((reason) => setError(reason.message)); }, [postId]);
  if (error) return <main className="min-h-screen bg-bg p-12 text-text-1"><div role="alert">{error}</div></main>;
  if (!item) return <main className="min-h-screen bg-bg p-16 text-center text-text-2">Loading discussion…</main>;
  const solution = item.attachments.find((value) => value.type === 'solution');
  return <main className="min-h-screen bg-bg px-5 py-12 text-text-1"><div className="mx-auto max-w-3xl"><p className="text-xs font-bold uppercase tracking-[0.18em] text-accent-text">Citizen discussion</p><h1 className="mt-4 font-display text-4xl">{item.body}</h1><p className="mt-3 text-sm text-text-3">{item.author.display_name}</p><section className="mt-10 space-y-3">{item.replies.length ? item.replies.map((reply) => <article key={reply.id} className="rounded-card border border-border bg-surface p-5"><p>{reply.body}</p><p className="mt-2 text-xs text-text-3">{reply.author.display_name}</p></article>) : <p className="text-text-2">No replies yet. Use the authenticated Discuss experience in the mobile app to reply.</p>}</section><div className="mt-10 flex gap-5">{solution && <Link className="text-accent-text underline" to={`/issues/housing-rent/solutions/${solution.reference_id}`}>Return to solution</Link>}<Link className="text-accent-text underline" to="/issues/housing-rent">Official evidence</Link></div></div></main>;
}
