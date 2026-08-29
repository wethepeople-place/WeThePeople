import { FormEvent, useCallback, useEffect, useState } from 'react';
import { ImagePlus, Link2, Send, Video, X } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';

import { CitizenSolution, createCitizenSolution, fetchSolutions, setSolutionVote } from '../api/civic';
import DiscussionVideoEmbed from '../components/DiscussionVideoEmbed';
import { fetchIssueAgenda } from '../api/issues';
import { useAuth } from '../contexts/AuthContext';

const SOCIAL_URL = /https:\/\/(?:www\.)?(?:youtube\.com|youtu\.be|tiktok\.com|facebook\.com|fb\.watch|instagram\.com)\/[^\s]+/i;

function titleFrom(text: string) {
  const firstLine = text.trim().split(/\n|[.!?]\s/)[0].replace(SOCIAL_URL, '').trim();
  const value = firstLine || 'Community solution';
  return value.length > 100 ? `${value.slice(0, 97).trim()}…` : value;
}

export default function SolutionsPage() {
  const { slug = 'housing-rent' } = useParams();
  const { isAuthenticated } = useAuth();
  const returnPath = `/issues/${slug}/solutions`;
  const fallbackTitle = slug.split('-').map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(' ');
  const [issueTitle, setIssueTitle] = useState(fallbackTitle);
  const [items, setItems] = useState<CitizenSolution[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [text, setText] = useState('');

  const load = useCallback(() => {
    setLoading(true); setError('');
    fetchSolutions(slug).then((result) => setItems(result.items)).catch((reason) => setError(reason.message)).finally(() => setLoading(false));
  }, [slug]);

  useEffect(load, [load]);
  useEffect(() => { fetchIssueAgenda().then((agenda) => setIssueTitle(agenda.items.find((item) => item.slug === slug)?.title || fallbackTitle)).catch(() => undefined); }, [fallbackTitle, slug]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setSaving(true); setError('');
    const clean = text.trim();
    const videoUrl = clean.match(SOCIAL_URL)?.[0] || null;
    try {
      await createCitizenSolution({ issue_slug: slug, title: titleFrom(clean), summary: clean.slice(0, 1000), body: clean, video_url: videoUrl });
      setText(''); setShowForm(false); load();
    } catch (reason) { setError((reason as Error).message); } finally { setSaving(false); }
  };

  const vote = async (item: CitizenSolution, choice: 'support' | 'oppose') => {
    if (!isAuthenticated) return;
    try { const result = await setSolutionVote(item.id, item.current_user_choice === choice ? null : choice); setItems((current) => current.map((value) => value.id === item.id ? { ...value, ...result } : value)); }
    catch (reason) { setError((reason as Error).message); }
  };

  return <main className="min-h-screen bg-bg px-4 py-8 text-text-1 sm:px-8 sm:py-12"><div className="mx-auto max-w-4xl">
    <p className="text-xs font-bold uppercase tracking-[0.18em] text-accent-text">{issueTitle}</p>
    <div className="mt-3 flex flex-wrap items-end justify-between gap-4"><div><h1 className="font-display text-4xl sm:text-5xl">Citizen solutions</h1><p className="mt-3 max-w-2xl text-text-2">Share an idea, a link, or a provider-hosted video.</p></div>
      {isAuthenticated ? <button className="inline-flex min-h-12 items-center gap-2 rounded-xl bg-accent px-5 font-bold text-slate-950" onClick={() => setShowForm((value) => !value)}>{showForm ? <><X className="h-5 w-5" />Close</> : 'Share a solution'}</button> : <Link className="rounded-xl bg-accent px-5 py-3 font-bold text-slate-950" to={`/login?next=${encodeURIComponent(returnPath)}`}>Sign in to share</Link>}
    </div>

    {showForm && <form className="mt-8 rounded-2xl border border-border bg-surface p-4 sm:p-6" onSubmit={submit}>
      <label className="sr-only" htmlFor="solution-text">Share your solution</label>
      <textarea id="solution-text" autoFocus required minLength={20} maxLength={10000} rows={8} value={text} onChange={(event) => setText(event.target.value)} placeholder={`Share your solution for ${issueTitle}…\n\nPaste a link anywhere to include it.`} className="w-full resize-y rounded-xl border border-border bg-bg p-4 text-lg leading-7 outline-none placeholder:text-text-3 focus:border-accent focus:ring-2 focus:ring-accent/25" />
      <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-border pt-3">
        <span className="inline-flex min-h-10 items-center gap-2 rounded-full bg-bg px-3 text-sm text-text-2"><Link2 className="h-4 w-4" />Paste links in the text</span>
        <button type="button" disabled title="Image uploads require scanning, re-encoding, metadata removal, moderation, and deletion controls" className="inline-flex min-h-10 items-center gap-2 rounded-full border border-border px-3 text-sm opacity-55"><ImagePlus className="h-4 w-4" />Image soon</button>
        <button type="button" disabled title="Native video uploads require the approved media safety gate" className="inline-flex min-h-10 items-center gap-2 rounded-full border border-border px-3 text-sm opacity-55"><Video className="h-4 w-4" />Video upload soon</button>
        <button disabled={saving || text.trim().length < 20} className="ml-auto inline-flex min-h-11 items-center gap-2 rounded-xl bg-accent px-5 font-bold text-slate-950 disabled:opacity-50"><Send className="h-4 w-4" />{saving ? 'Publishing…' : 'Publish'}</button>
      </div>
      <p className="mt-3 text-xs leading-5 text-text-3">YouTube, TikTok, Facebook, and Instagram links are normalized and remain consent-gated. Published solutions are public and linked to your account.</p>
    </form>}

    {error && <div role="alert" className="mt-6 rounded-xl border border-red-500/50 bg-red-950/30 p-4">{error} <button className="ml-2 underline" onClick={load}>Retry</button></div>}
    {loading ? <p className="mt-10 text-text-2">Loading solutions…</p> : items.length === 0 ? <div className="mt-10 rounded-2xl border border-border bg-surface p-8"><h2 className="text-xl font-semibold">No published solutions yet</h2><p className="mt-2 text-text-2">Be the first to share an idea for {issueTitle}.</p></div> : <div className="mt-10 space-y-5">{items.map((item) => <article key={item.id} className="rounded-2xl border border-border bg-surface p-6"><h2 className="text-2xl font-semibold"><Link className="hover:text-accent-text" to={`/issues/${slug}/solutions/${item.id}`}>{item.title}</Link></h2><p className="mt-3 whitespace-pre-wrap leading-7 text-text-2">{item.summary}</p>{item.video_link && item.discussion_post_id && <DiscussionVideoEmbed video={item.video_link} title={item.title} postId={item.discussion_post_id} />}<div className="mt-5 flex flex-wrap gap-3">{isAuthenticated ? <><button aria-pressed={item.current_user_choice === 'support'} onClick={() => vote(item, 'support')} className="rounded-lg border border-emerald-500 px-4 py-2">Support · {item.vote_totals.support}</button><button aria-pressed={item.current_user_choice === 'oppose'} onClick={() => vote(item, 'oppose')} className="rounded-lg border border-rose-500 px-4 py-2">Oppose · {item.vote_totals.oppose}</button></> : <Link className="rounded-lg border border-accent px-4 py-2 text-accent-text" to={`/login?next=${encodeURIComponent(returnPath)}`}>Sign in to Support or Oppose</Link>}</div>{!isAuthenticated && <p className="mt-3 text-xs leading-5 text-text-3">Signing in returns you here. No vote is submitted automatically.</p>}<p className="mt-4 text-xs leading-5 text-text-3">{item.vote_rule} Current ballots: {item.vote_totals.total_ballots}.</p><Link className="mt-4 inline-block text-sm text-accent-text underline" to={`/issues/${slug}/solutions/${item.id}`}>Open solution</Link></article>)}</div>}
    <p className="mt-10"><Link className="text-accent-text underline" to={`/issues/${slug}`}>Return to official evidence</Link></p>
  </div></main>;
}
