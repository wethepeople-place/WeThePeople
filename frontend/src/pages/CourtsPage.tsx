import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { fetchCourtCases, type CourtCaseItem } from '../api/courts';

export default function CourtsPage() {
  const [params] = useSearchParams();
  const issue = params.get('issue') || '';
  const bill = params.get('bill') || '';
  const [items, setItems] = useState<CourtCaseItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    fetchCourtCases(issue || undefined, bill || undefined).then((result) => active && setItems(result.items)).catch((reason) => active && setError(reason.message)).finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [issue, bill]);

  return <main className="min-h-screen bg-bg px-5 py-12 text-text-1"><div className="mx-auto max-w-4xl">
    <p className="text-xs font-bold uppercase tracking-[0.18em] text-accent-text">Courts</p>
    <h1 className="mt-3 font-display text-4xl sm:text-5xl">Related lawsuits and proceedings</h1>
    <p className="mt-3 max-w-3xl text-text-2">Source-backed court activity with explicit procedural status. Allegations are not findings, and filings are not decisions.</p>
    {issue && <p className="mt-4"><Link className="text-accent-text underline" to={`/issues/${issue}`}>Return to official issue evidence</Link></p>}
    {bill && <p className="mt-4"><Link className="text-accent-text underline" to={`/politics/bill/${bill}`}>Return to bill details</Link></p>}
    {loading && <p className="mt-10 text-text-2">Loading court records…</p>}
    {error && <p className="mt-10 rounded-card border border-border bg-surface p-6 text-text-2">{error}</p>}
    {!loading && !error && items.length === 0 && <div className="mt-10 rounded-card border border-border bg-surface p-8"><h2 className="text-xl font-semibold">No reviewed court proceedings yet</h2><p className="mt-2 text-text-2">Cases appear only after authoritative sources and procedural status have been reviewed.</p></div>}
    <section className="mt-10 space-y-5">{items.map((item) => <article key={item.case_id} className="rounded-card border border-border bg-surface p-6">
      <p className="text-xs font-bold uppercase tracking-wide text-accent-text">{item.procedural_status.replaceAll('_', ' ')}</p>
      <h2 className="mt-2 text-2xl font-semibold"><Link to={`/courts/${item.case_id}${bill ? `?bill=${encodeURIComponent(bill)}` : ''}`}>{item.case_name}</Link></h2>
      <p className="mt-2 text-text-2">{item.court_name} · Docket {item.docket_number}</p>
      <a className="mt-4 inline-block text-sm text-accent-text underline" href={item.docket_url} target="_blank" rel="noreferrer">Authoritative docket</a>
    </article>)}</section>
  </div></main>;
}
