import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { ChevronDown, ImagePlus, Link2, Send, X } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';

import { CitizenSolution, createCitizenSolution, fetchSolutions, setSolutionVote } from '../api/civic';
import { fetchIssueAgenda } from '../api/issues';
import { useAuth } from '../contexts/AuthContext';

const fieldClass = 'mt-2 w-full rounded-xl border border-border bg-bg px-4 py-3 text-base outline-none placeholder:text-text-3 focus:border-accent focus:ring-2 focus:ring-accent/25';

export default function SolutionsPage() {
  const { slug = 'housing-rent' } = useParams();
  const { isAuthenticated } = useAuth();
  const returnPath = `/issues/${slug}/solutions`;
  const draftKey = `wtp-solution-draft:${slug}`;
  const fallbackTitle = slug.split('-').map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(' ');
  const [issueTitle, setIssueTitle] = useState(fallbackTitle);
  const [items, setItems] = useState<CitizenSolution[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [title, setTitle] = useState('');
  const [idea, setIdea] = useState('');
  const [details, setDetails] = useState('');
  const [tradeoffs, setTradeoffs] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');

  const load = useCallback(() => {
    setLoading(true); setError('');
    fetchSolutions(slug).then((result) => setItems(result.items)).catch((reason) => setError(reason.message)).finally(() => setLoading(false));
  }, [slug]);

  useEffect(load, [load]);
  useEffect(() => { fetchIssueAgenda().then((agenda) => setIssueTitle(agenda.items.find((item) => item.slug === slug)?.title || fallbackTitle)).catch(() => undefined); }, [fallbackTitle, slug]);
  useEffect(() => {
    try {
      const draft = JSON.parse(localStorage.getItem(draftKey) || 'null');
      if (draft) { setTitle(draft.title || ''); setIdea(draft.idea || ''); setDetails(draft.details || ''); setTradeoffs(draft.tradeoffs || ''); setSourceUrl(draft.sourceUrl || ''); }
    } catch { /* Ignore an invalid local draft. */ }
  }, [draftKey]);

  const body = useMemo(() => [details && `How it could work\n${details}`, tradeoffs && `Tradeoffs to consider\n${tradeoffs}`, sourceUrl && `Supporting link\n${sourceUrl}`].filter(Boolean).join('\n\n') || idea, [details, idea, sourceUrl, tradeoffs]);
  const saveDraft = () => { localStorage.setItem(draftKey, JSON.stringify({ title, idea, details, tradeoffs, sourceUrl })); };
  const clearComposer = () => { setTitle(''); setIdea(''); setDetails(''); setTradeoffs(''); setSourceUrl(''); setShowDetails(false); setShowPreview(false); localStorage.removeItem(draftKey); };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setSaving(true); setError('');
    try {
      await createCitizenSolution({ issue_slug: slug, title: title.trim(), summary: idea.trim(), body });
      clearComposer(); setShowForm(false); load();
    } catch (reason) { setError((reason as Error).message); } finally { setSaving(false); }
  };

  const vote = async (item: CitizenSolution, choice: 'support' | 'oppose') => {
    if (!isAuthenticated) return;
    try { const result = await setSolutionVote(item.id, item.current_user_choice === choice ? null : choice); setItems((current) => current.map((value) => value.id === item.id ? { ...value, ...result } : value)); }
    catch (reason) { setError((reason as Error).message); }
  };

  return <main className="min-h-screen bg-bg px-4 py-8 text-text-1 sm:px-8 sm:py-12"><div className="mx-auto max-w-4xl">
    <p className="text-xs font-bold uppercase tracking-[0.18em] text-accent-text">{issueTitle}</p>
    <div className="mt-3 flex flex-wrap items-end justify-between gap-4"><div><h1 className="font-display text-4xl sm:text-5xl">Citizen solutions</h1><p className="mt-3 max-w-2xl text-text-2">Share an idea for improving this issue. You can keep it short and add evidence or tradeoffs if you have them.</p></div>
      {isAuthenticated ? <button className="inline-flex min-h-12 items-center gap-2 rounded-xl bg-accent px-5 font-bold text-slate-950" onClick={() => setShowForm((value) => !value)}>{showForm ? <><X className="h-5 w-5" />Close</> : 'Share a solution'}</button> : <Link className="rounded-xl bg-accent px-5 py-3 font-bold text-slate-950" to={`/login?next=${encodeURIComponent(returnPath)}`}>Sign in to share</Link>}
    </div>

    {showForm && <form className="mt-8 rounded-2xl border border-border bg-surface p-5 sm:p-7" onSubmit={submit}>
      <h2 className="text-2xl font-bold">What’s your solution?</h2><p className="mt-1 text-sm text-text-2">Start with the idea. Everything else is optional.</p>
      <label className="mt-6 block font-semibold">Give it a short name<input autoFocus required minLength={5} maxLength={120} value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Example: Make shelter applications easier" className={fieldClass} /><span className="mt-1 block text-right text-xs text-text-3">{title.length}/120</span></label>
      <label className="mt-4 block font-semibold">What should change?<textarea required minLength={10} maxLength={1000} rows={4} value={idea} onChange={(event) => setIdea(event.target.value)} placeholder="Explain your idea in a few plain sentences." className={fieldClass} /><span className="mt-1 block text-right text-xs text-text-3">{idea.length}/1000</span></label>
      <label className="mt-4 block font-semibold"><span className="inline-flex items-center gap-2"><Link2 className="h-4 w-4" />Add a supporting link <span className="font-normal text-text-3">(optional)</span></span><input type="url" value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} placeholder="https://…" className={fieldClass} /></label>
      <div className="mt-3 flex items-start gap-3 rounded-xl border border-border bg-bg/60 p-4 text-sm text-text-2"><ImagePlus className="mt-0.5 h-5 w-5 shrink-0" /><p><strong className="text-text-1">Images are coming next.</strong> Uploads will open after privacy-safe storage, metadata removal, scanning, moderation, and deletion controls are ready.</p></div>
      <button type="button" className="mt-5 inline-flex min-h-11 items-center gap-2 font-semibold text-accent-text" aria-expanded={showDetails} onClick={() => setShowDetails((value) => !value)}><ChevronDown className={`h-5 w-5 transition ${showDetails ? 'rotate-180' : ''}`} />Add details or tradeoffs</button>
      {showDetails && <div className="mt-2 grid gap-4 sm:grid-cols-2"><label className="block font-semibold">How could it work?<textarea maxLength={4000} rows={5} value={details} onChange={(event) => setDetails(event.target.value)} placeholder="Steps, cost, or who could make it happen…" className={fieldClass} /></label><label className="block font-semibold">What are the tradeoffs?<textarea maxLength={4000} rows={5} value={tradeoffs} onChange={(event) => setTradeoffs(event.target.value)} placeholder="Possible downsides, risks, or open questions…" className={fieldClass} /></label></div>}
      {showPreview && <section className="mt-6 rounded-xl border border-accent/40 bg-bg p-5" aria-label="Solution preview"><p className="text-xs font-bold uppercase tracking-wider text-accent-text">Preview</p><h3 className="mt-2 text-2xl font-bold">{title || 'Your solution title'}</h3><p className="mt-3 whitespace-pre-wrap text-text-2">{idea || 'Your short explanation will appear here.'}</p>{body !== idea && <p className="mt-4 whitespace-pre-wrap border-t border-border pt-4 text-sm text-text-2">{body}</p>}</section>}
      <div className="mt-6 flex flex-wrap gap-3"><button disabled={saving || title.trim().length < 5 || idea.trim().length < 10} className="inline-flex min-h-12 items-center gap-2 rounded-xl bg-accent px-5 font-bold text-slate-950 disabled:opacity-50"><Send className="h-4 w-4" />{saving ? 'Publishing…' : 'Publish solution'}</button><button type="button" className="min-h-12 rounded-xl border border-border px-5 font-semibold" onClick={() => setShowPreview((value) => !value)}>{showPreview ? 'Hide preview' : 'Preview'}</button><button type="button" className="min-h-12 px-3 font-semibold text-text-2 underline" onClick={saveDraft}>Save draft on this device</button></div>
      <p className="mt-4 text-xs leading-5 text-text-3">Published solutions are public and linked to your account. Citizen proposals are separate from official evidence.</p>
    </form>}

    {error && <div role="alert" className="mt-6 rounded-xl border border-red-500/50 bg-red-950/30 p-4">{error} <button className="ml-2 underline" onClick={load}>Retry</button></div>}
    {loading ? <p className="mt-10 text-text-2">Loading solutions…</p> : items.length === 0 ? <div className="mt-10 rounded-2xl border border-border bg-surface p-8"><h2 className="text-xl font-semibold">No published solutions yet</h2><p className="mt-2 text-text-2">Be the first to share an idea for {issueTitle}.</p></div> : <div className="mt-10 space-y-5">{items.map((item) => <article key={item.id} className="rounded-2xl border border-border bg-surface p-6"><h2 className="text-2xl font-semibold"><Link className="hover:text-accent-text" to={`/issues/${slug}/solutions/${item.id}`}>{item.title}</Link></h2><p className="mt-3 leading-7 text-text-2">{item.summary}</p><div className="mt-5 flex flex-wrap gap-3">{isAuthenticated ? <><button aria-pressed={item.current_user_choice === 'support'} onClick={() => vote(item, 'support')} className="rounded-lg border border-emerald-500 px-4 py-2">Support · {item.vote_totals.support}</button><button aria-pressed={item.current_user_choice === 'oppose'} onClick={() => vote(item, 'oppose')} className="rounded-lg border border-rose-500 px-4 py-2">Oppose · {item.vote_totals.oppose}</button></> : <Link className="rounded-lg border border-accent px-4 py-2 text-accent-text" to={`/login?next=${encodeURIComponent(returnPath)}`}>Sign in to Support or Oppose</Link>}</div>{!isAuthenticated && <p className="mt-3 text-xs leading-5 text-text-3">Signing in returns you here. No vote is submitted automatically.</p>}<p className="mt-4 text-xs leading-5 text-text-3">{item.vote_rule} Current ballots: {item.vote_totals.total_ballots}.</p><Link className="mt-4 inline-block text-sm text-accent-text underline" to={`/issues/${slug}/solutions/${item.id}`}>Read full solution and revisions</Link></article>)}</div>}
    <p className="mt-10"><Link className="text-accent-text underline" to={`/issues/${slug}`}>Return to official evidence</Link></p>
  </div></main>;
}
