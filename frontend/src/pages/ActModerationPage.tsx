import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { CheckCircle2, EyeOff, ShieldCheck } from 'lucide-react';
import { fetchActModerationQueue, moderateActItem, type ActModerationItem } from '../api/civic';
import { useAuth } from '../contexts/AuthContext';

export default function ActModerationPage() {
  const { user, loading: authLoading } = useAuth();
  const [items, setItems] = useState<ActModerationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState('');

  const load = () => {
    setLoading(true); setError('');
    fetchActModerationQueue().then((result) => setItems(result.items)).catch((err) => setError(err instanceof Error ? err.message : 'Could not load the moderation queue.')).finally(() => setLoading(false));
  };
  useEffect(load, []);

  if (authLoading) return <main className="min-h-screen bg-bg px-4 py-12 text-text-1"><p>Checking administrator access…</p></main>;
  if (!user) return <Navigate to={`/login?next=${encodeURIComponent('/act/moderation')}`} replace />;
  if (user.role !== 'admin') return <Navigate to="/act" replace />;

  const decide = async (item: ActModerationItem, status: 'published' | 'hidden') => {
    const key = `${item.kind}:${item.id}`;
    const reason = (reasons[key] || '').trim();
    if (reason.length < 10) { setError('Add a review reason of at least 10 characters.'); return; }
    setBusy(key); setError(''); setNotice('');
    try {
      await moderateActItem(item, status, reason);
      setItems((current) => current.filter((entry) => `${entry.kind}:${entry.id}` !== key));
      setNotice(`${item.kind === 'circle' ? 'Circle' : 'Activity'} ${status === 'published' ? 'published' : 'hidden'} with an audit record.`);
    } catch (err) { setError(err instanceof Error ? err.message : 'The review decision could not be saved.'); }
    finally { setBusy(''); }
  };

  return <main className="min-h-screen bg-bg px-4 py-10 text-text-1 sm:px-6 lg:px-8">
    <div className="mx-auto max-w-5xl">
      <div className="flex items-center gap-3"><ShieldCheck className="h-8 w-8 text-amber-300" /><div><p className="text-xs font-bold uppercase tracking-[0.2em] text-amber-300">Administrator</p><h1 className="text-3xl font-black">ACT moderation</h1></div></div>
      <p className="mt-4 max-w-3xl leading-7 text-text-2">Review proposed Action Circles and civic activities before they become public. Member and attendee identities are never shown here.</p>
      {notice && <p role="status" className="mt-6 rounded-xl border border-emerald-400/30 bg-emerald-400/10 p-4 text-emerald-200">{notice}</p>}
      {error && <div role="alert" className="mt-6 rounded-xl border border-red-400/30 bg-red-400/10 p-4 text-red-200"><p>{error}</p><button className="mt-3 font-bold underline" onClick={load}>Try again</button></div>}
      {loading ? <p className="mt-8 text-text-2">Loading proposed actions…</p> : items.length === 0 ? <section className="mt-8 rounded-2xl border border-white/10 bg-white/5 p-8"><CheckCircle2 className="h-8 w-8 text-emerald-300" /><h2 className="mt-3 text-xl font-bold">Nothing is waiting for review</h2><p className="mt-2 text-text-2">New proposals will appear here without exposing participant lists.</p></section> : <div className="mt-8 space-y-6">
        {items.map((item) => {
          const key = `${item.kind}:${item.id}`;
          return <article key={key} className="rounded-2xl border border-white/10 bg-white/5 p-5 sm:p-6">
            <div className="flex flex-wrap items-center gap-2 text-xs font-bold uppercase tracking-wider"><span className="rounded-full bg-amber-300/10 px-3 py-1 text-amber-200">{item.kind}</span><span className="text-text-2">Submitted by {item.organizer.display_name}</span></div>
            <h2 className="mt-4 text-xl font-bold">{item.name || item.title}</h2>
            {item.objective && <p className="mt-2 font-semibold text-text-1">{item.objective}</p>}
            <p className="mt-3 whitespace-pre-wrap leading-7 text-text-2">{item.description}</p>
            {item.kind === 'circle' ? <dl className="mt-4 grid gap-2 text-sm text-text-2 sm:grid-cols-2"><div><dt className="font-bold text-text-1">Civic target</dt><dd>{item.target_type}: {item.target_id}</dd></div><div><dt className="font-bold text-text-1">Membership</dt><dd>{item.membership_mode}</dd></div><div className="sm:col-span-2"><dt className="font-bold text-text-1">Conduct rules</dt><dd>{item.conduct_rules}</dd></div><div className="sm:col-span-2"><dt className="font-bold text-text-1">Completion condition</dt><dd>{item.completion_condition}</dd></div></dl> : <dl className="mt-4 grid gap-2 text-sm text-text-2 sm:grid-cols-2"><div><dt className="font-bold text-text-1">When</dt><dd>{item.starts_at ? new Date(item.starts_at).toLocaleString() : 'Not provided'} · {item.timezone}</dd></div><div><dt className="font-bold text-text-1">Format</dt><dd>{item.format} · {item.host_type}</dd></div>{item.public_url && <div className="sm:col-span-2"><dt className="font-bold text-text-1">Public link</dt><dd className="break-all">{item.public_url}</dd></div>}</dl>}
            <label className="mt-5 block text-sm font-bold" htmlFor={`reason-${key}`}>Review reason <span className="font-normal text-text-2">(stored in the private audit trail)</span></label>
            <textarea id={`reason-${key}`} value={reasons[key] || ''} onChange={(event) => setReasons((current) => ({ ...current, [key]: event.target.value }))} maxLength={1000} className="mt-2 min-h-24 w-full rounded-xl border border-white/15 bg-black/20 p-3 text-text-1" placeholder="Explain why this proposal is safe to publish or should remain hidden." />
            <div className="mt-4 flex flex-col gap-3 sm:flex-row"><button disabled={busy === key} onClick={() => decide(item, 'published')} className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-emerald-400 px-4 font-bold text-black disabled:opacity-50"><CheckCircle2 className="h-4 w-4" />Publish</button><button disabled={busy === key} onClick={() => decide(item, 'hidden')} className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-white/20 px-4 font-bold disabled:opacity-50"><EyeOff className="h-4 w-4" />Keep hidden</button></div>
          </article>;
        })}
      </div>}
    </div>
  </main>;
}
