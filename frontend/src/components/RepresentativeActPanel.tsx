import { useEffect, useMemo, useState } from 'react';
import { Check, Clipboard, ExternalLink, Megaphone, Phone, X } from 'lucide-react';
import { Link } from 'react-router-dom';

import { fetchRepresentativeActOptions, saveActReceipt, type RepresentativeActOptions } from '../api/civic';
import { useAuth } from '../contexts/AuthContext';

type Props = {
  personId: string;
  displayName: string;
  issueSlug?: string;
};

function receiptKey(personId: string, kind: 'call' | 'message') {
  return `rep-${personId}-${kind}`;
}

export default function RepresentativeActPanel({ personId, displayName, issueSlug = '' }: Props) {
  const { isAuthenticated } = useAuth();
  const [open, setOpen] = useState(false);
  const [options, setOptions] = useState<RepresentativeActOptions | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [message, setMessage] = useState('');

  const contextLabel = useMemo(() => issueSlug ? issueSlug.replaceAll('-', ' ') : 'this civic issue', [issueSlug]);

  useEffect(() => {
    if (!open || options) return;
    setLoading(true); setError('');
    void fetchRepresentativeActOptions(personId)
      .then((result) => {
        setOptions(result);
        setMessage(`Hello ${result.representative.display_name},\n\nI am a constituent writing about ${contextLabel}. I am asking your office to review the evidence and explain what action you will take.\n\nThank you.`);
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : 'Official contact options could not load.'))
      .finally(() => setLoading(false));
  }, [contextLabel, open, options, personId]);

  const record = async (kind: 'call' | 'message', status: 'opened' | 'user_confirmed_submitted') => {
    setNotice('');
    try {
      await saveActReceipt({
        idempotency_key: receiptKey(personId, kind), action_kind: kind,
        target_type: 'representative', target_id: personId, representative_id: personId,
        status, allow_aggregate: false,
      });
      setNotice(status === 'opened' ? 'Saved privately as opened.' : 'Saved privately as completed by you.');
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'The private receipt could not be saved.'); }
  };

  const copyMessage = async () => {
    try {
      await navigator.clipboard.writeText(message);
      setNotice('Message copied. Review it again before submitting through the official form.');
      if (isAuthenticated) await record('message', 'opened');
    } catch { setError('Copy failed. Select the message and copy it manually.'); }
  };

  return <>
    <button type="button" onClick={() => setOpen(true)} className="mt-3 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border border-amber-400/40 bg-amber-400/10 px-4 py-2 text-sm font-bold text-amber-200 outline-none hover:bg-amber-400/15 focus-visible:ring-4 focus-visible:ring-amber-300/60">
      <Megaphone className="h-4 w-4" /> ACT: contact office
    </button>
    {open && <div className="fixed inset-0 z-[80] grid place-items-end bg-black/70 md:place-items-center" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setOpen(false); }}>
      <section role="dialog" aria-modal="true" aria-label={`Contact ${displayName}`} className="max-h-[90vh] w-full overflow-y-auto rounded-t-3xl border border-white/10 bg-[#0b1322] p-5 text-white shadow-2xl md:max-w-2xl md:rounded-3xl md:p-7">
        <header className="flex items-start justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-widest text-amber-300">ACT · constituent contact</p><h2 className="mt-1 text-2xl font-bold">Contact {displayName}</h2><p className="mt-2 text-sm leading-6 text-slate-300">You choose what to say and complete every action yourself. WeThePeople never sends messages or places calls for you.</p></div><button autoFocus type="button" onClick={() => setOpen(false)} className="grid min-h-11 min-w-11 place-content-center rounded-full bg-white/10" aria-label="Close ACT panel"><X className="h-5 w-5" /></button></header>
        {loading && <p className="mt-6 text-slate-300">Loading verified public office information…</p>}
        {error && <p role="alert" className="mt-5 rounded-xl border border-rose-400/30 bg-rose-400/10 p-3 text-rose-200">{error}</p>}
        {options && <div className="mt-6 space-y-6">
          <section><h3 className="font-bold">Call a public office</h3><div className="mt-3 grid gap-3 sm:grid-cols-2">
            {options.contacts.filter((item) => item.phone).map((item) => <a key={item.id} href={`tel:${item.phone}`} onClick={() => { if (isAuthenticated) void record('call', 'opened'); }} className="rounded-2xl border border-white/15 bg-white/5 p-4 outline-none focus-visible:ring-4 focus-visible:ring-amber-300/60"><span className="flex items-center gap-2 font-bold"><Phone className="h-4 w-4" />{item.label}</span><span className="mt-2 block text-lg text-amber-200">{item.phone}</span><span className="mt-1 block text-xs text-slate-400">Verified from {item.source.publisher}</span></a>)}
            <a href={`tel:${options.fallback.phone}`} onClick={() => { if (isAuthenticated) void record('call', 'opened'); }} className="rounded-2xl border border-white/15 bg-white/5 p-4 outline-none focus-visible:ring-4 focus-visible:ring-amber-300/60"><span className="flex items-center gap-2 font-bold"><Phone className="h-4 w-4" />{options.fallback.label}</span><span className="mt-2 block text-lg text-amber-200">{options.fallback.phone}</span><span className="mt-1 block text-xs text-slate-400">Official switchboard · ask for the office</span></a>
          </div></section>
          <section><label htmlFor={`act-message-${personId}`} className="font-bold">Prepare your message</label><textarea id={`act-message-${personId}`} rows={7} maxLength={5000} value={message} onChange={(event) => setMessage(event.target.value)} className="mt-3 w-full rounded-2xl border border-white/15 bg-black/20 p-4 leading-6 text-white outline-none focus-visible:ring-4 focus-visible:ring-amber-300/60" /><div className="mt-3 flex flex-wrap gap-2"><button type="button" onClick={() => void copyMessage()} className="inline-flex min-h-11 items-center gap-2 rounded-full bg-amber-300 px-5 py-2 font-bold text-slate-950"><Clipboard className="h-4 w-4" />Copy message</button>{options.contacts.filter((item) => item.contact_url).map((item) => <a key={item.id} href={item.contact_url!} target="_blank" rel="noreferrer" onClick={() => { if (isAuthenticated) void record('message', 'opened'); }} className="inline-flex min-h-11 items-center gap-2 rounded-full border border-white/20 px-5 py-2 font-bold"><ExternalLink className="h-4 w-4" />Open {item.label}</a>)}</div><p className="mt-3 text-xs leading-5 text-slate-400">{options.message_policy.instructions}</p></section>
          <section className="rounded-2xl border border-white/10 bg-white/5 p-4"><h3 className="font-bold">Private action receipt</h3>{isAuthenticated ? <><p className="mt-1 text-sm text-slate-300">Receipts are private by default and never contain your message or call information.</p><button type="button" onClick={() => void record('message', 'user_confirmed_submitted')} className="mt-3 inline-flex min-h-11 items-center gap-2 rounded-full border border-white/20 px-4 py-2 font-bold"><Check className="h-4 w-4" />I submitted it myself</button></> : <p className="mt-1 text-sm text-slate-300"><Link className="font-bold text-amber-300 underline" to="/login">Sign in</Link> if you want to save a private receipt. You can still call or copy without an account.</p>}</section>
          {notice && <p role="status" className="text-sm text-amber-200">{notice}</p>}
        </div>}
      </section>
    </div>}
  </>;
}
