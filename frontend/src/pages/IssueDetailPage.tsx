import { useEffect, useState } from 'react';
import { ArrowLeft, BarChart3, ChevronRight, ExternalLink, FileText, Flag, Landmark, Lightbulb, MessageCircle, Play, Scale, TrendingUp, Users } from 'lucide-react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { fetchIssueDetail, type EvidenceSeries, type FederalJob, type IssueBill, type IssueSource, type IssueSummary, type IssueVideo } from '../api/issues';
import IssueActionStrip from '../components/IssueActionStrip';

type State = { summary: IssueSummary; evidence: EvidenceSeries[]; bills: IssueBill[]; billTotal: number; videos: IssueVideo[]; videoTotal: number; federalJobs: FederalJob[]; federalJobTotal: number; federalJobsSource: IssueSource | null; availability: { evidence: boolean; bills: boolean; videos: boolean; federalJobs: boolean } };

const date = (value: string) => new Intl.DateTimeFormat('en-US', {
  year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC',
}).format(new Date(value));
const number = (value: number) => new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value);
const phaseLabel = { past: 'Resolved', current: 'In progress', upcoming: 'Upcoming', enacted: 'Enacted' } as const;

function Sparkline({ series }: { series: EvidenceSeries | undefined }) {
  const values = series?.observations.map((item) => item.value) || [];
  if (values.length < 2) return <div className="grid h-16 place-items-center rounded-xl bg-slate-50 text-xs font-semibold text-slate-500">Trend appears when two sourced observations are available</div>;
  const min = Math.min(...values);
  const range = Math.max(...values) - min || 1;
  const points = values.map((value, index) => `${(index / (values.length - 1)) * 300},${58 - ((value - min) / range) * 48}`).join(' ');
  return <svg viewBox="0 0 300 64" className="h-16 w-full" role="img" aria-label={`${series?.title} trend`}><polyline points={points} fill="none" stroke="#245b87" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}

function HubRow({ icon: Icon, label, detail, to }: { icon: typeof Play; label: string; detail: string; to: string }) {
  return <Link to={to} className="group flex min-h-16 items-center gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2.5 outline-none transition hover:border-[#245b87] focus-visible:ring-4 focus-visible:ring-sky-200">
    <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-[#245b87] text-white"><Icon className="h-4.5 w-4.5" aria-hidden="true" /></span>
    <span className="min-w-0 flex-1"><span className="block font-black leading-5 text-slate-950">{label}</span><span className="block text-xs leading-4 text-slate-500">{detail}</span></span>
    <ChevronRight className="h-5 w-5 shrink-0 text-slate-400 transition group-hover:translate-x-0.5 group-hover:text-[#245b87]" aria-hidden="true" />
  </Link>;
}

function Source({ source }: { source: { url: string; publisher: string; retrieved_at: string } }) {
  return <p className="mt-4 text-xs text-text-2">
    Source: <a className="text-accent-text hover:underline" href={source.url} target="_blank" rel="noreferrer">
      {source.publisher} <ExternalLink className="inline h-3 w-3" />
    </a> · Retrieved {date(source.retrieved_at)}
  </p>;
}

export default function IssueDetailPage() {
  const { slug = 'housing-rent' } = useParams();
  const { hash } = useLocation();
  const [data, setData] = useState<State | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    fetchIssueDetail(slug).then((result) => active && setData(result)).catch((reason) => active && setError(reason.message));
    return () => { active = false; };
  }, [slug]);

  useEffect(() => {
    if (!data || !hash) return;
    const target = document.getElementById(hash.slice(1));
    target?.scrollIntoView({ block: 'start' });
  }, [data, hash]);

  if (error) return <main className="min-h-screen bg-bg px-6 py-16 text-text-1"><div className="mx-auto max-w-3xl rounded-card border border-border bg-surface p-8"><h1 className="font-display text-3xl">Issue hub</h1><p className="mt-3 text-text-2">{error}. Please try again.</p></div></main>;
  if (!data) return <main className="min-h-screen bg-bg p-16 text-center text-text-2">Loading sourced issue data…</main>;

  const leadSeries = data.evidence.find((series) => series.observations.length > 1) || data.evidence[0];
  const firstVideo = data.videos[0];

  return <main id="main-content" className="min-h-screen bg-[#edede9] pb-32 text-slate-950 md:pb-20">
    <header className="bg-[#245b87] px-5 py-5 text-white md:py-8">
      <div className="mx-auto max-w-3xl">
        <Link to="/civic" className="inline-flex min-h-11 items-center gap-1 text-sm font-bold text-sky-50"><ArrowLeft className="h-4 w-4" />Agenda</Link>
        <p className="mt-1 text-xs font-bold uppercase tracking-[.16em] text-sky-100">Issue hub</p>
        <h1 className="mt-1 text-3xl font-black tracking-tight md:text-5xl">{data.summary.title}</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-sky-50 md:text-base">{data.summary.summary || 'Reviewed public evidence, legislation, solutions, and ways to participate.'}</p>
      </div>
    </header>

    <div className="mx-auto max-w-3xl px-3 py-3 sm:px-6 md:py-7">
      <section aria-labelledby="issue-snapshot" className="rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex items-start justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-[.14em] text-slate-500">Sourced snapshot</p><h2 id="issue-snapshot" className="mt-1 font-black">{leadSeries?.title || 'Sourced evidence'}</h2></div><span className="shrink-0 rounded-md bg-emerald-50 px-2 py-1 text-[.65rem] font-black uppercase tracking-wide text-emerald-800">Sourced data</span></div>
        <div className="mt-3"><Sparkline series={leadSeries} /></div>
        {leadSeries ? <p className="mt-2 text-xs text-slate-500">{leadSeries.observations.length} sourced {leadSeries.observations.length === 1 ? 'observation' : 'observations'} · {leadSeries.source.publisher}</p> : <p className="mt-2 text-xs text-slate-500">No sourced observations are connected yet.</p>}
      </section>

      <section aria-label="Issue coverage" className="mt-2 grid grid-cols-3 divide-x divide-slate-200 rounded-2xl border border-slate-200 bg-white py-3 text-center">
        <div><p className="text-lg font-black text-[#245b87]">{data.evidence.length}</p><p className="text-[.7rem] text-slate-500">evidence series</p></div>
        <div><p className="text-lg font-black text-[#245b87]">{data.billTotal}</p><p className="text-[.7rem] text-slate-500">official bills</p></div>
        <div><p className="text-lg font-black text-[#245b87]">{data.videoTotal}</p><p className="text-[.7rem] text-slate-500">linked videos</p></div>
      </section>

      <div className="mt-2"><Link to={`/issues/${slug}/solutions`} className="flex min-h-12 items-center justify-center gap-2 rounded-xl bg-[#245b87] px-4 font-black text-white outline-none focus-visible:ring-4 focus-visible:ring-sky-200"><Lightbulb className="h-5 w-5" />Explore and propose solutions</Link></div>

      <nav aria-label="Explore this issue" className="mt-3 space-y-2">
        <HubRow icon={Play} label="Videos" detail={data.availability.videos ? `${data.videoTotal} linked civic ${data.videoTotal === 1 ? 'video' : 'videos'}` : 'Video connections temporarily unavailable'} to={firstVideo ? `/watch/${firstVideo.video_id}` : `/issues/${slug}#watch`} />
        <HubRow icon={BarChart3} label="Sourced evidence" detail={data.availability.evidence ? `${data.evidence.length} sourced evidence series` : 'Evidence temporarily unavailable'} to={`/issues/${slug}#evidence`} />
        <HubRow icon={Lightbulb} label="Citizen solutions" detail="Review proposals and their evidence" to={`/issues/${slug}/solutions`} />
        <HubRow icon={Users} label="Representatives" detail="Find officials for your address" to={`/politics/find-rep?issue=${encodeURIComponent(slug)}`} />
        <HubRow icon={Landmark} label="Legislation" detail={`${data.billTotal} Congress.gov ${data.billTotal === 1 ? 'bill' : 'bills'} connected`} to={`/issues/${slug}#legislation`} />
        <HubRow icon={Flag} label="Elections" detail="Make a private voting plan" to={`/elections?issue=${encodeURIComponent(slug)}`} />
        <HubRow icon={MessageCircle} label="Discuss" detail="Join the evidence-linked conversation" to={`/discuss?issue=${encodeURIComponent(slug)}`} />
      </nav>

      <Link to={`/act?target_type=issue&target_id=${encodeURIComponent(slug)}`} className="mt-2 flex min-h-12 items-center justify-center gap-2 rounded-xl bg-[#dda91f] px-4 font-black text-slate-950 outline-none focus-visible:ring-4 focus-visible:ring-amber-200"><Scale className="h-5 w-5" />Take action on this issue</Link>

      <details className="mt-5 rounded-2xl border border-slate-200 bg-white p-4 md:p-5">
        <summary className="cursor-pointer font-black text-[#245b87]">All issue links</summary>
        <div className="mt-4 text-sm"><IssueActionStrip issueSlug={slug} evidenceCount={data.evidence.length} billCount={data.billTotal} /></div>
      </details>

      <section id="watch" className="mt-14 scroll-mt-24">
        <div className="flex items-center gap-3"><Play className="text-[#245b87]" /><h2 className="text-2xl font-black">Civic videos</h2></div>
        {!data.availability.videos ? <p className="mt-5 rounded-card border border-border bg-surface p-5 text-text-2">Watch videos are temporarily unavailable. The rest of this issue hub remains accessible.</p>
          : data.videos.length === 0 ? <p className="mt-5 text-text-2">No linked civic videos are connected to this issue yet.</p>
            : <><div className="mt-6 grid gap-4 md:grid-cols-3">{data.videos.map((video) => <Link key={video.video_id} className="rounded-card border border-border bg-surface p-5 transition hover:border-accent/60 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-accent/30" to={`/watch/${video.video_id}`}>
              <p className="text-xs font-bold uppercase tracking-wider text-accent-text">{video.content_origin === 'community' ? 'Community shared' : 'Reviewed source'}</p>
              <h3 className="mt-2 text-lg font-semibold leading-6">{video.caption}</h3>
              <p className="mt-3 text-sm text-text-2">{video.creator_label}</p>
            </Link>)}</div>{data.videoTotal > data.videos.length && <p className="mt-4 text-sm text-slate-500">Showing the latest {data.videos.length} of {data.videoTotal} linked videos.</p>}</>}
      </section>

      {slug === 'jobs-unemployment' && <section id="federal-jobs" className="mt-14 scroll-mt-24">
        <div className="flex items-center gap-3"><Users className="text-[#245b87]" /><h2 className="text-2xl font-black">Federal jobs now open</h2></div>
        {!data.availability.federalJobs && <p className="mt-5 rounded-card border border-border bg-surface p-5 text-text-2">USAJOBS is temporarily unavailable. Other issue connections remain accessible.</p>}
        {data.availability.federalJobs && <>
          <p className="mt-2 text-sm text-text-2">{data.federalJobTotal.toLocaleString()} current USAJOBS listings. Showing {data.federalJobs.length} official listings.</p>
          <div className="mt-6 grid gap-4 md:grid-cols-2">{data.federalJobs.map((job) => <article key={`${job.url}-${job.position_title}`} className="rounded-card border border-border bg-surface p-5">
            <p className="text-xs font-bold uppercase tracking-wider text-accent-text">{job.organization_name || job.department_name}</p>
            <h3 className="mt-2 text-lg font-semibold">{job.position_title}</h3>
            <p className="mt-2 text-sm text-text-2">{job.location || 'Location listed on USAJOBS'}{job.schedule_type ? ` · ${job.schedule_type}` : ''}</p>
            <a className="mt-4 inline-flex min-h-11 items-center text-sm font-bold text-accent-text hover:underline" href={job.url} target="_blank" rel="noreferrer">View official listing <ExternalLink className="ml-1 h-4 w-4" /></a>
          </article>)}</div>
          {data.federalJobsSource && <Source source={data.federalJobsSource} />}
        </>}
      </section>}

      <section id="evidence" className="mt-14 scroll-mt-24">
        <div className="flex items-center gap-3"><TrendingUp className="text-[#245b87]" /><h2 className="text-2xl font-black">What the evidence shows</h2></div>
        {!data.availability.evidence && <p className="mt-5 rounded-card border border-border bg-surface p-5 text-text-2">Evidence is temporarily unavailable. Other issue connections remain accessible.</p>}
        {data.availability.evidence && data.evidence.length === 0 && <p className="mt-5 text-text-2">No sourced evidence series are connected yet.</p>}
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

      <section id="legislation" className="mt-14 scroll-mt-24">
        <div className="flex items-center gap-3"><Landmark className="text-[#245b87]" /><h2 className="text-2xl font-black">Legislation to follow</h2></div>
        {!data.availability.bills && <p className="mt-5 rounded-card border border-border bg-surface p-5 text-text-2">Legislation is temporarily unavailable. Other issue connections remain accessible.</p>}
        {data.availability.bills && data.bills.length === 0 && <p className="mt-5 text-text-2">No official bills are connected yet.</p>}
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
        {data.billTotal > data.bills.length && <p className="mt-4 text-sm text-slate-500">Showing the latest {data.bills.length} of {data.billTotal} connected Congress.gov bills.</p>}
      </section>
    </div>
  </main>;
}
