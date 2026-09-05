import { FormEvent, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { CitizenSolution, fetchSolution, fetchSolutionRevisions, reviseSolution, setSolutionVote, SolutionRevisionItem } from '../api/civic';
import DiscussionVideoEmbed from '../components/DiscussionVideoEmbed';
import { useAuth } from '../contexts/AuthContext';

export default function SolutionDetailPage() {
  const { slug = 'housing-rent', solutionId = '' } = useParams();
  const id = Number(solutionId);
  const { user, isAuthenticated } = useAuth();
  const [item, setItem] = useState<CitizenSolution | null>(null);
  const [revisions, setRevisions] = useState<SolutionRevisionItem[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);

  const load = () => {
    setLoading(true); setError('');
    Promise.all([fetchSolution(slug, id), fetchSolutionRevisions(id).catch(() => ({ items: [] }))])
      .then(([solution, history]) => { setItem(solution); setRevisions(history.items); })
      .catch((reason) => setError(reason.message)).finally(() => setLoading(false));
  };
  useEffect(load, [slug, id]);

  const vote = async (choice: 'support' | 'oppose') => {
    if (!item || !isAuthenticated) return;
    try { const result = await setSolutionVote(item.id, item.current_user_choice === choice ? null : choice); setItem({ ...item, ...result }); }
    catch (reason) { setError((reason as Error).message); }
  };

  const revise = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); if (!item) return;
    const data = new FormData(event.currentTarget);
    try {
      await reviseSolution(item.id, { title: String(data.get('title')), summary: String(data.get('summary')), body: String(data.get('body')), change_note: String(data.get('change_note')) });
      setEditing(false); load();
    } catch (reason) { setError((reason as Error).message); }
  };

  if (loading) return <main className="min-h-screen bg-bg p-16 text-center text-text-2">Loading solution…</main>;
  if (error || !item) return <main className="min-h-screen bg-bg p-12 text-text-1"><div role="alert" className="mx-auto max-w-3xl rounded-card border border-red-500/50 p-6">{error || 'Solution unavailable'} <button className="underline" onClick={load}>Retry</button></div></main>;
  if (item.status === 'removed' || item.status === 'duplicate') return <main className="min-h-screen bg-bg p-12 text-text-1"><div className="mx-auto max-w-3xl rounded-card border border-border bg-surface p-8"><h1 className="font-display text-3xl">{item.message}</h1>{item.duplicate_of_solution_id && <Link className="mt-5 inline-block text-accent-text underline" to={`/issues/${slug}/solutions/${item.duplicate_of_solution_id}`}>Open the canonical solution</Link>}<p className="mt-6"><Link className="text-accent-text underline" to={`/issues/${slug}/solutions`}>Return to solutions</Link></p></div></main>;

  const canEdit = item.status === 'published' && user?.id === item.creator_user_id;
  const issueName = slug.split('-').map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(' ');
  const returnPath = `/issues/${slug}/solutions/${item.id}`;
  return <main className="min-h-screen bg-bg px-5 py-12 text-text-1"><article className="mx-auto max-w-4xl">
    <p className="text-xs font-bold uppercase tracking-[0.18em] text-accent-text">{issueName} · Community proposal</p>
    <h1 className="mt-4 font-display text-4xl sm:text-6xl">{item.title}</h1><p className="mt-4 text-sm text-text-3">By {item.creator_display_name} · Revision {item.latest_revision_number}</p>
    <p className="mt-7 text-xl leading-8 text-text-2">{item.summary}</p><div className="mt-8 whitespace-pre-wrap rounded-card border border-border bg-surface p-6 leading-8">{item.body}</div>
    {item.video_link && item.discussion_post_id && <DiscussionVideoEmbed video={item.video_link} title={item.title} postId={item.discussion_post_id} />}
    {item.status === 'closed' && <p className="mt-6 rounded border border-amber-500/50 bg-amber-950/20 p-4 text-amber-100">This solution is closed. Its published record and revision history remain readable, but it no longer accepts revisions or votes.</p>}
    <div className="mt-6 flex flex-wrap gap-3">{isAuthenticated ? <><button disabled={item.status !== 'published'} aria-pressed={item.current_user_choice === 'support'} onClick={() => vote('support')} className="rounded border border-emerald-500 px-4 py-2 disabled:opacity-50">Support · {item.vote_totals.support}</button><button disabled={item.status !== 'published'} aria-pressed={item.current_user_choice === 'oppose'} onClick={() => vote('oppose')} className="rounded border border-rose-500 px-4 py-2 disabled:opacity-50">Oppose · {item.vote_totals.oppose}</button></> : item.status === 'published' ? <Link className="rounded border border-accent px-4 py-2 text-accent-text" to={`/login?next=${encodeURIComponent(returnPath)}`}>Sign in to Support or Oppose</Link> : null}{canEdit && <button className="rounded border border-accent px-4 py-2" onClick={() => setEditing((value) => !value)}>Revise</button>}</div>
    {!isAuthenticated && item.status === 'published' && <p className="mt-3 text-xs leading-5 text-text-3">Signing in returns you here. No vote is submitted automatically.</p>}
    <p className="mt-4 text-xs leading-5 text-text-3">{item.vote_rule} Current ballots: {item.vote_totals.total_ballots}.</p>
    {editing && <form className="mt-8 space-y-4 rounded-card border border-accent/50 bg-surface p-6" onSubmit={revise}><label className="block">Title<input name="title" required minLength={5} maxLength={500} defaultValue={item.title} className="mt-1 w-full rounded border border-border bg-bg p-3" /></label><label className="block">Summary<textarea name="summary" required minLength={10} maxLength={1000} defaultValue={item.summary} className="mt-1 w-full rounded border border-border bg-bg p-3" /></label><label className="block">Full proposal<textarea name="body" required minLength={20} maxLength={10000} rows={7} defaultValue={item.body} className="mt-1 w-full rounded border border-border bg-bg p-3" /></label><label className="block">What changed?<input name="change_note" required minLength={3} maxLength={500} className="mt-1 w-full rounded border border-border bg-bg p-3" /></label><button className="rounded bg-accent px-4 py-2 font-semibold text-slate-950">Save revision</button></form>}
    <section className="mt-12"><h2 className="font-display text-3xl">Revision history</h2><div className="mt-5 space-y-3">{revisions.map((revision) => <div key={revision.revision_number} className="rounded border border-border bg-surface p-4"><p className="font-semibold">Revision {revision.revision_number} · {revision.change_note}</p><p className="mt-1 text-sm text-text-3">{revision.editor_display_name} · {new Date(revision.created_at).toLocaleString()}</p></div>)}</div></section>
    <div className="mt-12 flex flex-wrap gap-5">
      {item.discussion_post_id && <Link className="text-accent-text underline" to={`/discuss/${item.discussion_post_id}`} state={{ returnAfterReply: true }}>Open citizen discussion</Link>}
      <Link className="text-accent-text underline" to={`/issues/${slug}`}>Return to official evidence</Link>
      <Link className="text-accent-text underline" to="/government">Government activity</Link>
      <Link className="text-accent-text underline" to={`/courts?issue=${encodeURIComponent(slug)}`}>Related court proceedings</Link>
      <Link className="text-accent-text underline" to={`/politics/find-rep?issue=${encodeURIComponent(slug)}`}>Contact your representatives</Link>
    </div>
  </article></main>;
}
