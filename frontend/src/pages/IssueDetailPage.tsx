import { useEffect, useState } from 'react';
import { ExternalLink, FileText, Landmark, TrendingUp } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { fetchIssueDetail, type EvidenceSeries, type IssueBill, type IssueSummary } from '../api/issues';

type State = { summary: IssueSummary; evidence: EvidenceSeries[]; bills: IssueBill[] };

const date = (value: string) => new Intl.DateTimeFormat('en-US', {
  year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC',
}).format(new Date(value));
const number = (value: number) => new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value);
const phaseLabel = { past: 'Resolved', current: 'In progress', upcoming: 'Upcoming' } as const;

function Source({ source }: { source: { url: string; publisher: string; retrieved_at: string } }) {
  return <p className="mt-4 text-xs text-text-2">
    Source: <a className="text-accent-text hover:underline" href={source.url} target="_blank" rel="noreferrer">
      {source.publisher} <ExternalLink className="inline h-3 w-3" />
    </a> · Retrieved {date(source.retrieved_at)}
  </p>;
}

export default function IssueDetailPage() {
  const { slug = 'housing-rent' } = useParams();
  const [data, setData] = useState<State | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    fetchIssueDetail(slug).then((result) => active && setData(result)).catch((reason) => active && setError(reason.message));
    return () => { active = false; };
  }, [slug]);

  if (error) return <main className="min-h-screen bg-bg px-6 py-16 text-text-1"><div className="mx-auto max-w-3xl rounded-card border border-border bg-surface p-8"><h1 className="font-display text-3xl">Housing & Rent</h1><p className="mt-3 text-text-2">{error}. Load the reviewed local fixture, then try again.</p></div></main>;
  if (!data) return <main className="min-h-screen bg-bg p-16 text-center text-text-2">Loading sourced issue data…</main>;

  return <main className="min-h-screen bg-bg px-5 py-12 text-text-1 sm:px-8">
    <div className="mx-auto max-w-6xl">
      <p className="text-xs font-bold uppercase tracking-[0.18em] text-accent-text">Issue brief</p>
      <h1 className="mt-3 font-display text-4xl sm:text-6xl">{data.summary.title}</h1>
      <p className="mt-5 max-w-3xl text-lg leading-8 text-text-2">{data.summary.summary || 'Official evidence and federal legislation connected to housing affordability and rent.'}</p>
      <div className="mt-8 flex flex-wrap gap-3 text-sm text-text-2">
        <span className="rounded-pill border border-border bg-surface px-4 py-2">{data.evidence.length} evidence series</span>
        <span className="rounded-pill border border-border bg-surface px-4 py-2">{data.bills.length} reviewed bills</span>
        <Link className="rounded-pill border border-accent/50 bg-accent-dim px-4 py-2 text-accent-text" to={`/issues/${slug}/solutions`}>Citizen solutions</Link>
        <Link className="rounded-pill border border-accent/50 bg-accent-dim px-4 py-2 text-accent-text" to={`/discuss?issue=${encodeURIComponent(slug)}`}>Public discussion</Link>
        <Link className="rounded-pill border border-accent/50 bg-accent-dim px-4 py-2 text-accent-text" to="/government">Government activity</Link>
        <Link className="rounded-pill border border-accent/50 bg-accent-dim px-4 py-2 text-accent-text" to={`/politics/find-rep?issue=${encodeURIComponent(slug)}`}>Find your representatives</Link>
        <Link className="rounded-pill border border-accent/50 bg-accent-dim px-4 py-2 text-accent-text" to={`/courts?issue=${encodeURIComponent(slug)}`}>Related court proceedings</Link>
      </div>

      <section className="mt-14">
        <div className="flex items-center gap-3"><TrendingUp className="text-accent" /><h2 className="font-display text-3xl">What the evidence shows</h2></div>
        <div className="mt-6 grid gap-5 md:grid-cols-2">
          {data.evidence.map((series) => {
            const latest = series.observations.at(-1);
            return <article key={series.key} className="rounded-card border border-border bg-surface p-6">
              <p className="text-xs uppercase tracking-wider text-text-3">{series.geography.id} · {series.unit}</p>
              <h3 className="mt-2 text-xl font-semibold">{series.title}</h3>
              {latest ? <><p className="mt-7 font-mono text-4xl text-text-1">{number(latest.value)}</p><p className="mt-1 text-sm text-text-2">Latest observation · {date(latest.date)}</p></> : <p className="mt-7 text-text-2">No observations loaded.</p>}
              <Source source={series.source} />
            </article>;
          })}
        </div>
      </section>

      <section className="mt-14">
        <div className="flex items-center gap-3"><Landmark className="text-accent" /><h2 className="font-display text-3xl">Legislation to follow</h2></div>
        <div className="mt-6 space-y-4">
          {data.bills.map((bill) => <article key={bill.bill_id} className="rounded-card border border-border bg-surface p-5 sm:p-6">
            <div className="flex flex-col justify-between gap-4 sm:flex-row">
              <div><p className="font-mono text-xs uppercase text-accent-text">{bill.bill_type.toUpperCase()} {bill.bill_number} · {bill.congress}th Congress</p><h3 className="mt-2 text-lg font-semibold">{bill.title || bill.bill_id}</h3>{bill.relevance_note && <p className="mt-2 text-sm leading-6 text-text-2">{bill.relevance_note}</p>}</div>
              <span className="h-fit shrink-0 rounded-pill bg-accent-dim px-3 py-1 text-xs font-semibold text-accent-text">{phaseLabel[bill.phase]}</span>
            </div>
            {bill.latest_action_text && <p className="mt-4 border-l-2 border-accent/50 pl-4 text-sm text-text-2">{bill.latest_action_text}</p>}
            <div className="flex flex-wrap items-end justify-between gap-3"><Source source={bill.source} /><Link className="text-sm text-accent-text hover:underline" to={`/politics/bill/${bill.bill_id}`}>Bill details <FileText className="inline h-4 w-4" /></Link></div>
          </article>)}
        </div>
      </section>
    </div>
  </main>;
}
