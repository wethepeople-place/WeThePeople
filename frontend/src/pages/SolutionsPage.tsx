import { FormEvent, useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { CitizenSolution, createCitizenSolution, fetchSolutions, setSolutionVote } from '../api/civic';
import { useAuth } from '../contexts/AuthContext';

export default function SolutionsPage() {
  const { slug = 'housing-rent' } = useParams();
  const { isAuthenticated } = useAuth();
  const [items, setItems] = useState<CitizenSolution[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    setLoading(true); setError('');
    fetchSolutions(slug).then((result) => setItems(result.items)).catch((reason) => setError(reason.message)).finally(() => setLoading(false));
  }, [slug]);
  useEffect(load, [load]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setSaving(true); setError('');
    const data = new FormData(event.currentTarget);
    try {
      await createCitizenSolution({ issue_slug: slug, title: String(data.get('title')), summary: String(data.get('summary')), body: String(data.get('body')) });
      setShowForm(false); load();
    } catch (reason) { setError((reason as Error).message); } finally { setSaving(false); }
  };

  const vote = async (item: CitizenSolution, choice: 'support' | 'oppose') => {
    if (!isAuthenticated) return;
    try {
      const result = await setSolutionVote(item.id, item.current_user_choice === choice ? null : choice);
      setItems((current) => current.map((value) => value.id === item.id ? { ...value, ...result } : value));
    } catch (reason) { setError((reason as Error).message); }
  };

  return <main className="min-h-screen bg-bg px-5 py-12 text-text-1 sm:px-8"><div className="mx-auto max-w-4xl">
    <p className="text-xs font-bold uppercase tracking-[0.18em] text-accent-text">Housing &amp; Rent</p>
    <div className="mt-3 flex flex-wrap items-end justify-between gap-4"><div><h1 className="font-display text-4xl sm:text-5xl">Citizen solutions</h1><p className="mt-3 max-w-2xl text-text-2">Structured proposals from participating users. Citizen opinion is separate from official evidence.</p></div>
      {isAuthenticated ? <button className="rounded-lg bg-accent px-4 py-2 font-semibold text-slate-950" onClick={() => setShowForm((value) => !value)}>Submit a solution</button> : <Link className="text-accent-text underline" to="/login">Log in to submit or vote</Link>}
    </div>
    {showForm && <form className="mt-8 space-y-4 rounded-card border border-border bg-surface p-6" onSubmit={submit}>
      <label className="block text-sm">Title<input required minLength={5} maxLength={500} name="title" className="mt-1 w-full rounded border border-border bg-bg p-3" /></label>
      <label className="block text-sm">Summary<textarea required minLength={10} maxLength={1000} name="summary" className="mt-1 w-full rounded border border-border bg-bg p-3" /></label>
      <label className="block text-sm">Proposal and tradeoffs<textarea required minLength={20} maxLength={10000} name="body" rows={6} className="mt-1 w-full rounded border border-border bg-bg p-3" /></label>
      <button disabled={saving} className="rounded-lg bg-accent px-4 py-2 font-semibold text-slate-950 disabled:opacity-50">{saving ? 'Publishing…' : 'Publish solution'}</button>
    </form>}
    {error && <div role="alert" className="mt-6 rounded border border-red-500/50 bg-red-950/30 p-4">{error} <button className="ml-2 underline" onClick={load}>Retry</button></div>}
    {loading ? <p className="mt-10 text-text-2">Loading solutions…</p> : items.length === 0 ? <div className="mt-10 rounded-card border border-border bg-surface p-8"><h2 className="text-xl font-semibold">No published solutions yet</h2><p className="mt-2 text-text-2">A reviewed Housing &amp; Rent solution will appear here when loaded.</p></div> : <div className="mt-10 space-y-5">{items.map((item) => <article key={item.id} className="rounded-card border border-border bg-surface p-6">
      <h2 className="text-2xl font-semibold"><Link className="hover:text-accent-text" to={`/issues/${slug}/solutions/${item.id}`}>{item.title}</Link></h2><p className="mt-3 leading-7 text-text-2">{item.summary}</p>
      <div className="mt-5 flex flex-wrap gap-3"><button disabled={!isAuthenticated} aria-pressed={item.current_user_choice === 'support'} onClick={() => vote(item, 'support')} className="rounded border border-emerald-500 px-4 py-2 disabled:opacity-50">Support · {item.vote_totals.support}</button><button disabled={!isAuthenticated} aria-pressed={item.current_user_choice === 'oppose'} onClick={() => vote(item, 'oppose')} className="rounded border border-rose-500 px-4 py-2 disabled:opacity-50">Oppose · {item.vote_totals.oppose}</button></div>
      <p className="mt-4 text-xs leading-5 text-text-3">{item.vote_rule} Current ballots: {item.vote_totals.total_ballots}.</p>
      <Link className="mt-4 inline-block text-sm text-accent-text underline" to={`/issues/${slug}/solutions/${item.id}`}>Read full solution and revisions</Link>
    </article>)}</div>}
    <p className="mt-10"><Link className="text-accent-text underline" to={`/issues/${slug}`}>Return to official evidence</Link></p>
  </div></main>;
}
