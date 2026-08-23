import { useEffect, useState } from 'react';
import { ArrowRight, ChevronDown, ChevronUp, ExternalLink, MessageSquarePlus } from 'lucide-react';
import { Link } from 'react-router-dom';

import { fetchIssueAgenda, type IssueAgenda } from '../api/issues';

const formatSurveyDates = (start: string, end: string) => {
  const formatter = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
  return `${formatter.format(new Date(`${start}T00:00:00Z`))}–${formatter.format(new Date(`${end}T00:00:00Z`))}`;
};

export default function AgendaPage() {
  const [agenda, setAgenda] = useState<IssueAgenda | null>(null);
  const [error, setError] = useState('');
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    let active = true;
    fetchIssueAgenda().then((value) => active && setAgenda(value)).catch(() => active && setError('The public-priorities agenda is temporarily unavailable.'));
    return () => { active = false; };
  }, []);

  const visibleItems = agenda?.items.slice(0, showAll ? agenda.items.length : 5) || [];
  const remaining = Math.max(0, (agenda?.items.length || 0) - 5);

  return <main id="main-content" className="min-h-screen bg-[#e9eef4] pb-32 text-slate-950 md:pb-20">
    <header className="bg-[#245b87] px-5 py-6 text-white md:py-9">
      <div className="mx-auto max-w-3xl">
        <p className="text-xs font-bold uppercase tracking-[.16em] text-sky-100">We the People</p>
        <h1 className="mt-1 text-3xl font-black tracking-tight md:text-5xl">The People&apos;s Agenda</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-sky-50 md:text-base">Twenty issues Americans named for government attention, connected to WTP receipts, solutions, representatives, elections, discussion, and action.</p>
      </div>
    </header>

    <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 md:py-7">
      <section aria-labelledby="agenda-methodology" className="rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
        <h2 id="agenda-methodology" className="text-sm font-black text-[#245b87]">{agenda?.methodology.label || 'Loading public priorities…'}</h2>
        {agenda && <>
          <p className="mt-1 text-sm text-slate-700">Ranked from a probability-based survey of <strong>{agenda.methodology.sample_size.toLocaleString()} U.S. adults</strong> · {formatSurveyDates(agenda.methodology.survey_start, agenda.methodology.survey_end)}</p>
          <p className="mt-1 text-xs leading-5 text-slate-500">Respondents could name up to five priorities · margin of sampling error ±{agenda.methodology.margin_of_error_points.toFixed(1)} points</p>
        </>}
      </section>

      {error && <p role="alert" className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">{error}</p>}

      <section aria-labelledby="published-issues" className="mt-4">
        <div className="flex items-end justify-between gap-3 px-1">
          <div><p className="text-xs font-bold uppercase tracking-[.14em] text-slate-500">The agenda</p><h2 id="published-issues" className="text-xl font-black">Top public priorities</h2></div>
          {agenda && <span className="text-xs font-semibold text-slate-500">{agenda.total} issues</span>}
        </div>

        <div className="mt-3 space-y-2.5">
          {!agenda && !error && [1, 2, 3, 4, 5].map((item) => <div key={item} className="h-24 animate-pulse rounded-2xl border border-slate-200 bg-white" />)}
          {visibleItems.map((item) => <Link key={item.slug} to={`/issues/${item.slug}`} className="group block rounded-2xl border border-slate-200 bg-white p-3.5 shadow-sm transition hover:border-[#245b87] hover:shadow-md focus:outline-none focus-visible:ring-4 focus-visible:ring-sky-200 sm:p-4">
            <div className="flex gap-3">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[#245b87] text-base font-black text-white" aria-label={`Agenda position ${item.rank}`}>{item.rank}</span>
              <div className="min-w-0 flex-1">
                <div className="flex items-start justify-between gap-3">
                  <h3 className="text-lg font-black leading-6">{item.title}</h3>
                  <span className="shrink-0 text-sm font-bold text-[#245b87]" aria-label={`${item.priority_share} percent named this priority`}>{item.priority_share}%</span>
                </div>
                <p className="mt-0.5 line-clamp-2 text-sm leading-5 text-slate-600">{item.evidence_note || item.summary || 'Reviewed receipts are being assembled.'}</p>
                <div className="mt-2.5 h-1.5 overflow-hidden rounded-full bg-slate-200" role="img" aria-label={item.priority_note}><div className="h-full rounded-full bg-[#245b87]" style={{ width: `${item.priority_share}%` }} /></div>
                <div className="mt-1.5 flex items-center justify-between gap-3 text-[11px] font-semibold text-slate-500">
                  <span>{item.priority_note}</span>
                  <ArrowRight className="h-4 w-4 shrink-0 transition group-hover:translate-x-1 group-hover:text-[#245b87]" aria-hidden="true" />
                </div>
              </div>
            </div>
          </Link>)}
        </div>

        {remaining > 0 && <button type="button" onClick={() => setShowAll((value) => !value)} className="mt-3 inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-4 text-sm font-black text-[#245b87] focus:outline-none focus-visible:ring-4 focus-visible:ring-sky-200">
          {showAll ? <><ChevronUp className="h-4 w-4" />Show top 5</> : <><ChevronDown className="h-4 w-4" />Show {remaining} more issues</>}
        </button>}
      </section>

      <Link to="/discuss?compose=1#composer" className="mt-4 inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-[#dda91f] px-5 font-black text-slate-950"><MessageSquarePlus className="h-5 w-5" />Propose an issue</Link>

      {agenda && <section id="how-ranking-works" className="mt-6 scroll-mt-24 rounded-2xl border border-slate-200 bg-white p-5">
        <h2 className="font-black">How this ranking works</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">{agenda.methodology.description} Percentages are the share who named an issue among up to five responses; they are not WTP votes and do not sum to 100. {agenda.methodology.tie_break}</p>
        <p className="mt-2 text-sm leading-6 text-slate-600">Issue pages without reviewed receipts clearly show that evidence, solutions, and legislation are still being assembled. WTP does not manufacture content to make a hub appear complete.</p>
        <a href={agenda.methodology.source_url} target="_blank" rel="noreferrer" className="mt-3 inline-flex min-h-11 items-center gap-1.5 font-bold text-[#245b87] underline">View AP-NORC source <ExternalLink className="h-4 w-4" /></a>
      </section>}
    </div>
  </main>;
}
