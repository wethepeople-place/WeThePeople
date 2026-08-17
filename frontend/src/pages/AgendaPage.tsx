import { useEffect, useState } from 'react';
import { ArrowRight, CalendarDays, FileText, Lightbulb, MessageSquarePlus } from 'lucide-react';
import { Link } from 'react-router-dom';

import { fetchIssueAgenda, type IssueAgenda } from '../api/issues';

const formatUpdated = (value: string | null) => value
  ? new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(value))
  : 'as sources are reviewed';

export default function AgendaPage() {
  const [agenda, setAgenda] = useState<IssueAgenda | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    fetchIssueAgenda().then((value) => active && setAgenda(value)).catch(() => active && setError('The issue catalog is temporarily unavailable.'));
    return () => { active = false; };
  }, []);

  return <main id="main-content" className="min-h-screen bg-[#edf1f5] pb-32 text-slate-950 md:pb-20">
    <header className="bg-[#245b87] px-5 py-6 text-white md:py-9">
      <div className="mx-auto max-w-3xl">
        <p className="text-xs font-bold uppercase tracking-[.16em] text-sky-100">We the People</p>
        <h1 className="mt-1 text-3xl font-black tracking-tight md:text-5xl">The People&apos;s Agenda</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-sky-50 md:text-base">Start with the issues WTP can support with reviewed public evidence, then follow the receipts into solutions and action.</p>
      </div>
    </header>

    <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 md:py-7">
      <section aria-labelledby="agenda-methodology" className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm md:p-5">
        <div className="flex items-start gap-3">
          <CalendarDays className="mt-0.5 h-5 w-5 shrink-0 text-[#245b87]" aria-hidden="true" />
          <div>
            <h2 id="agenda-methodology" className="font-black">{agenda?.methodology.label || 'Initial agenda'}</h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">{agenda?.methodology.description || 'Loading the reviewed issue catalog…'}</p>
            <p className="mt-1 text-xs text-slate-500">Updated {formatUpdated(agenda?.methodology.updated_at || null)} · <a className="font-semibold underline" href="#how-ranking-works">methodology</a></p>
          </div>
        </div>
      </section>

      {error && <p role="alert" className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">{error}</p>}

      <section aria-labelledby="published-issues" className="mt-4">
        <div className="flex items-end justify-between gap-3 px-1">
          <div><p className="text-xs font-bold uppercase tracking-[.14em] text-slate-500">The agenda</p><h2 id="published-issues" className="text-xl font-black">Published issue hubs</h2></div>
          {agenda && <span className="text-xs font-semibold text-slate-500">{agenda.total} reviewed</span>}
        </div>

        <div className="mt-3 space-y-3">
          {!agenda && !error && [1, 2].map((item) => <div key={item} className="h-28 animate-pulse rounded-2xl border border-slate-200 bg-white" />)}
          {agenda?.items.map((item) => <Link key={item.slug} to={`/issues/${item.slug}`} className="group block rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-[#245b87] hover:shadow-md focus:outline-none focus-visible:ring-4 focus-visible:ring-sky-200 md:p-5">
            <div className="flex gap-3">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#245b87] text-sm font-black text-white" aria-label={`Agenda position ${item.rank}`}>{item.rank}</span>
              <div className="min-w-0 flex-1">
                <div className="flex items-start justify-between gap-3"><h3 className="text-lg font-black leading-6">{item.title}</h3><ArrowRight className="mt-0.5 h-5 w-5 shrink-0 text-slate-400 transition group-hover:translate-x-1 group-hover:text-[#245b87]" aria-hidden="true" /></div>
                <p className="mt-1 text-sm leading-5 text-slate-600">{item.evidence_note || item.summary || 'Reviewed public evidence is being assembled.'}</p>
                <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs font-semibold text-slate-500"><span className="inline-flex items-center gap-1"><FileText className="h-3.5 w-3.5" />{item.evidence_series_count} evidence series</span><span>{item.bill_count} reviewed {item.bill_count === 1 ? 'bill' : 'bills'}</span></div>
                <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-200"><div className="h-full w-0 rounded-full bg-[#245b87]" /></div>
                <p className="mt-1.5 text-xs font-medium text-slate-500">Community score pending genuine participation</p>
              </div>
            </div>
          </Link>)}
        </div>

        {agenda?.total === 0 && <div className="mt-3 rounded-2xl border border-slate-200 bg-white p-6 text-center"><Lightbulb className="mx-auto h-7 w-7 text-[#245b87]" /><h3 className="mt-3 font-black">No issue hubs are published yet</h3><p className="mt-1 text-sm text-slate-600">WTP will list issues only after reviewed evidence is available.</p></div>}
      </section>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <Link to="/discuss?compose=1#composer" className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-[#dda91f] px-5 font-black text-slate-950"><MessageSquarePlus className="h-5 w-5" />Propose an issue</Link>
        {agenda?.items[0] && <Link to={`/issues/${agenda.items[0].slug}`} className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl border border-[#245b87] bg-white px-5 font-black text-[#245b87]">Explore the issue hub <ArrowRight className="h-4 w-4" /></Link>}
      </div>

      <section id="how-ranking-works" className="mt-6 scroll-mt-24 rounded-2xl border border-slate-200 bg-white p-5">
        <h2 className="font-black">How this initial agenda works</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">Issue hubs are currently ordered by the amount of reviewed source coverage available on WTP. This is not a public-opinion ranking. Community percentages will appear only after WTP has enough genuine, abuse-resistant participation and publishes the scoring method.</p>
        <Link to="/methodology" className="mt-3 inline-flex min-h-11 items-center font-bold text-[#245b87] underline">Read WTP methodology</Link>
      </section>
    </div>
  </main>;
}
