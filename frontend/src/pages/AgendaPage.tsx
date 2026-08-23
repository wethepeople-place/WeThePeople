import { useEffect, useState } from 'react';
import { ArrowRight, ChevronDown, ChevronUp, ExternalLink, Info, MessageSquarePlus } from 'lucide-react';
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

  return <main id="main-content" className="min-h-screen bg-[#e9eef4] pb-36 text-slate-950 md:pb-20">
    <header className="bg-[#245b87] px-5 py-5 text-white md:py-9">
      <div className="mx-auto max-w-3xl">
        <p className="text-xs font-bold uppercase tracking-[.16em] text-sky-100">We the People</p>
        <h1 className="mt-1 text-[1.75rem] font-black leading-tight tracking-tight md:text-5xl">The People&apos;s Agenda</h1>
        <p className="mt-3 hidden max-w-2xl text-sm leading-6 text-sky-50 sm:block md:text-base">Twenty issues Americans named for government attention, connected to WTP receipts, solutions, representatives, elections, discussion, and action.</p>
      </div>
    </header>

    <div className="mx-auto max-w-3xl px-3.5 py-3.5 sm:px-6 md:py-7">
      <section aria-labelledby="agenda-methodology" className="rounded-xl border border-slate-200 bg-white px-3.5 py-3 shadow-sm sm:rounded-2xl sm:px-4">
        <h2 id="agenda-methodology" className="sr-only">{agenda?.methodology.label || 'Loading public priorities…'}</h2>
        {agenda && <>
          <p className="text-sm leading-5 text-slate-700">Ranked from <strong>{agenda.methodology.sample_size.toLocaleString()} U.S. adults</strong> · {formatSurveyDates(agenda.methodology.survey_start, agenda.methodology.survey_end)}</p>
          <a href="#how-ranking-works" className="mt-1 inline-flex min-h-7 items-center gap-1 text-xs font-bold text-[#245b87] underline"><Info className="h-3.5 w-3.5" />How the ranking works</a>
        </>}
        {!agenda && !error && <p className="text-sm font-semibold text-slate-500">Loading public priorities…</p>}
      </section>

      {error && <p role="alert" className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">{error}</p>}

      <section aria-labelledby="published-issues" className="mt-3.5">
        <div className="flex items-end justify-between gap-3 px-1">
          <h2 id="published-issues" className="text-base font-black sm:text-xl">Top public priorities</h2>
          {agenda && <span className="text-xs font-semibold text-slate-500">{agenda.total} issues</span>}
        </div>

        <div className="mt-3 space-y-2.5">
          {!agenda && !error && [1, 2, 3, 4, 5].map((item) => <div key={item} className="h-24 animate-pulse rounded-xl border border-slate-200 bg-white sm:rounded-2xl" />)}
          {visibleItems.map((item) => <Link key={item.slug} to={`/issues/${item.slug}`} className="group block rounded-xl border border-slate-200 bg-white p-3 shadow-sm transition hover:border-[#245b87] hover:shadow-md focus:outline-none focus-visible:ring-4 focus-visible:ring-sky-200 sm:rounded-2xl sm:p-4">
            <div className="flex gap-3">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#245b87] text-sm font-black text-white sm:h-9 sm:w-9 sm:text-base" aria-label={`Agenda position ${item.rank}`}>{item.rank}</span>
              <div className="min-w-0 flex-1">
                <div className="flex items-start justify-between gap-3">
                  <h3 className="text-base font-black leading-5 sm:text-lg sm:leading-6">{item.title}</h3>
                  <span className="shrink-0 text-sm font-bold text-[#245b87]" aria-label={`${item.priority_share} percent named this priority`}>{item.priority_share}%</span>
                </div>
                <p className="mt-0.5 line-clamp-2 text-[13px] leading-[1.15rem] text-slate-600 sm:text-sm sm:leading-5">{item.evidence_note || item.summary || 'Reviewed receipts are being assembled.'}</p>
                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-200" role="img" aria-label={item.priority_note}><div className="h-full rounded-full bg-[#245b87]" style={{ width: `${item.priority_share}%` }} /></div>
                <div className="mt-1 flex items-center justify-end text-slate-500"><ArrowRight className="h-4 w-4 shrink-0 transition group-hover:translate-x-1 group-hover:text-[#245b87]" aria-hidden="true" /></div>
              </div>
            </div>
          </Link>)}
        </div>

        {remaining > 0 && <button type="button" onClick={() => setShowAll((value) => !value)} className="mt-3 inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-4 text-sm font-black text-[#245b87] focus:outline-none focus-visible:ring-4 focus-visible:ring-sky-200">
          {showAll ? <><ChevronUp className="h-4 w-4" />Show top 5</> : <><ChevronDown className="h-4 w-4" />Show {remaining} more issues</>}
        </button>}
      </section>

      <Link to="/discuss?compose=1#composer" className="mt-4 inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-[#dda91f] px-5 font-black text-slate-950"><MessageSquarePlus className="h-5 w-5" />Propose an issue</Link>

      {agenda && <details id="how-ranking-works" className="mt-5 scroll-mt-24 rounded-xl border border-slate-200 bg-white p-4 sm:rounded-2xl sm:p-5">
        <summary className="cursor-pointer font-black text-[#245b87]">How this ranking works</summary>
        <p className="mt-2 text-sm leading-6 text-slate-600">{agenda.methodology.description} Percentages are the share who named an issue among up to five responses; they are not WTP votes and do not sum to 100. {agenda.methodology.tie_break}</p>
        <p className="mt-2 text-sm leading-6 text-slate-600">Respondents could name up to five priorities. The sampling margin is ±{agenda.methodology.margin_of_error_points.toFixed(1)} points. Issue pages without reviewed receipts clearly say that material is still being assembled.</p>
        <a href={agenda.methodology.source_url} target="_blank" rel="noreferrer" className="mt-3 inline-flex min-h-11 items-center gap-1.5 font-bold text-[#245b87] underline">View AP-NORC source <ExternalLink className="h-4 w-4" /></a>
      </details>}
    </div>
  </main>;
}
