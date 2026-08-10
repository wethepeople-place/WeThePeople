import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { fetchCourtCase, type CourtCaseDetail } from '../api/courts';

export default function CourtCasePage() {
  const { caseId = '' } = useParams();
  const [params] = useSearchParams();
  const bill = params.get('bill') || '';
  const [item, setItem] = useState<CourtCaseDetail | null>(null);
  const [error, setError] = useState('');
  useEffect(() => { fetchCourtCase(caseId).then(setItem).catch((reason) => setError(reason.message)); }, [caseId]);
  if (error) return <main className="min-h-screen bg-bg p-12 text-text-1"><p>{error}</p><Link className="text-accent-text underline" to="/courts">Return to Courts</Link></main>;
  if (!item) return <main className="min-h-screen bg-bg p-12 text-text-2">Loading court case…</main>;
  return <main className="min-h-screen bg-bg px-5 py-12 text-text-1"><div className="mx-auto max-w-4xl">
    <p className="text-xs font-bold uppercase tracking-[0.18em] text-accent-text">{item.procedural_status.replaceAll('_', ' ')}</p>
    <h1 className="mt-3 font-display text-4xl">{item.case_name}</h1>
    <p className="mt-3 text-text-2">{item.court_name} · {item.jurisdiction} · Docket {item.docket_number}</p>
    <div className="mt-8 rounded-card border border-border bg-surface p-6"><h2 className="text-xl font-semibold">Procedural status</h2><p className="mt-2 text-text-2">{item.procedural_status.replaceAll('_', ' ')}</p>{item.disposition && <p className="mt-3">{item.disposition}</p>}</div>
    <section className="mt-8"><h2 className="text-2xl font-semibold">Parties</h2><div className="mt-3 space-y-2">{item.parties.map((party) => <p key={`${party.role}-${party.name}`}><span className="font-semibold">{party.role}:</span> {party.name}</p>)}</div></section>
    <section className="mt-8"><h2 className="text-2xl font-semibold">Docket timeline</h2><div className="mt-4 space-y-4">{item.events.map((event) => <article key={event.id} className="rounded-card border border-border bg-surface p-5"><p className="text-xs font-bold uppercase text-accent-text">{event.assertion_kind.replaceAll('_', ' ')} · {event.event_date}</p><p className="mt-2 leading-7">{event.summary}</p><a className="mt-3 inline-block text-sm text-accent-text underline" href={event.source.url} target="_blank" rel="noreferrer">Authoritative source</a></article>)}</div></section>
    <div className="mt-10 flex flex-wrap gap-5">
      {bill && <Link className="text-accent-text underline" to={`/politics/bill/${bill}`}>Return to bill details</Link>}
      <Link className="text-accent-text underline" to="/courts">All court proceedings</Link>
    </div>
  </div></main>;
}
