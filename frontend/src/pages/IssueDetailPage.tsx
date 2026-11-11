import { useEffect, useState } from 'react';
import {
  ArrowLeft, ArrowRight, ChevronDown, ChevronUp, ExternalLink, FileText,
  Landmark, MessageCircle, Play, Search, TrendingUp, Users, Vote,
} from 'lucide-react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import {
  fetchIssueDetail,
  type EvidenceSeries,
  type FederalJob,
  type IssueBill,
  type IssueSource,
  type IssueSummary,
  type IssueVideo,
} from '../api/issues';
import { getApiBaseUrl } from '../api/client';
import IssueVideoDialog from '../components/IssueVideoDialog';
import { ISSUE_TRENDS } from '../data/issueTrends';

type State = {
  summary: IssueSummary;
  evidence: EvidenceSeries[];
  bills: IssueBill[];
  billTotal: number;
  videos: IssueVideo[];
  videoTotal: number;
  federalJobs: FederalJob[];
  federalJobTotal: number;
  federalJobsSource: IssueSource | null;
  availability: { evidence: boolean; bills: boolean; videos: boolean; federalJobs: boolean };
};

const date = (value: string) => new Intl.DateTimeFormat('en-US', {
  year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC',
}).format(new Date(value));
const number = (value: number) => new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value);
const phaseLabel = { past: 'Resolved', current: 'In progress', upcoming: 'Upcoming', enacted: 'Enacted' } as const;

function videoThumbnail(video: IssueVideo) {
  const poster = video.delivery?.poster_url;
  if (poster) return poster.startsWith('/') ? `${getApiBaseUrl()}${poster}` : poster;
  if (video.delivery?.provider === 'youtube' && video.delivery.provider_video_id) return `https://i.ytimg.com/vi/${video.delivery.provider_video_id}/hqdefault.jpg`;
  return null;
}

function valueLabel(series: EvidenceSeries, value: number) {
  return series.unit.toLowerCase().includes('percent') ? `${number(value)}%` : `${number(value)} ${series.unit}`;
}

function evidenceExplanation(series: EvidenceSeries, issueTitle: string) {
  if (series.key.startsWith('census-net-international-migration')) {
    return 'People added to the U.S. population through international migration, minus people who left, during each annual estimate period. This is not a count of border encounters.';
  }
  if (series.unit.toLowerCase().includes('percent') && series.title.toLowerCase().includes('government priority')) {
    return `Share of U.S. adults who named ${issueTitle.toLowerCase()} as a 2026 government priority in the cited survey.`;
  }
  return `The latest sourced measure connected to ${issueTitle.toLowerCase()}.`;
}

function SourceLink({ source, checkedLabel = 'Source checked' }: { source: IssueSource; checkedLabel?: string }) {
  return <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs leading-5 text-slate-600">
    <a className="inline-flex min-h-8 items-center gap-1 font-bold text-[#164d78] underline decoration-[#164d78]/30 underline-offset-2 hover:decoration-[#164d78]" href={source.url} target="_blank" rel="noreferrer">
      {source.publisher}<ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
    </a>
    <span>{checkedLabel} {date(source.retrieved_at)}</span>
  </div>;
}

function EvidenceVisual({ series }: { series: EvidenceSeries }) {
  const observations = series.observations.slice(-6);
  if (observations.length === 1) {
    const observation = observations[0];
    const percentage = series.unit.toLowerCase().includes('percent');
    return <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 sm:p-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><p className="text-4xl font-black tracking-tight text-[#153f62] sm:text-5xl">{valueLabel(series, observation.value)}</p><p className="mt-1 text-sm font-semibold text-slate-600">Observation from {date(observation.date)}</p></div>
        <span className="rounded-full bg-white px-3 py-1 text-xs font-bold text-slate-600 ring-1 ring-slate-200">One sourced observation</span>
      </div>
      {percentage && <div className="mt-5" role="img" aria-label={`${valueLabel(series, observation.value)} on a scale from 0 to 100 percent`}>
        <div className="h-5 overflow-hidden rounded-full bg-slate-200"><div className="h-full rounded-full bg-[#245b87]" style={{ width: `${Math.max(0, Math.min(100, observation.value))}%` }} /></div>
        <div className="mt-1 flex justify-between text-[11px] font-semibold text-slate-500"><span>0%</span><span>50%</span><span>100%</span></div>
      </div>}
    </div>;
  }

  if (observations.length > 1) {
    const max = Math.max(...observations.map((item) => item.value)) || 1;
    const latest = observations.at(-1)!;
    const previous = observations.at(-2)!;
    const change = previous.value ? Math.round(((latest.value - previous.value) / previous.value) * 100) : 0;
    return <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 sm:p-5" role="img" aria-label={`${series.title}, ${observations.map((item) => `${new Date(item.date).getUTCFullYear()}: ${valueLabel(series, item.value)}`).join(', ')}`}>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-2"><p className="text-sm font-bold text-slate-700">Annual total</p><p className={`rounded-full px-3 py-1 text-xs font-black ${change < 0 ? 'bg-emerald-100 text-emerald-900' : 'bg-sky-100 text-sky-900'}`}>{Math.abs(change)}% {change < 0 ? 'lower' : 'higher'} than {new Date(previous.date).getUTCFullYear()}</p></div>
      <div className="overflow-x-auto pb-1"><div className="grid min-w-[620px] items-end gap-3 border-b border-slate-300 px-2 pt-8" style={{ gridTemplateColumns: `repeat(${observations.length}, minmax(88px, 1fr))` }}>
        {observations.map((item) => <div key={item.date} className="flex min-w-0 flex-col items-center justify-end"><span className="mb-2 whitespace-nowrap text-[11px] font-black text-[#153f62] sm:text-xs">{number(item.value)}</span><div className="w-full max-w-16 rounded-t-lg bg-[#245b87]" style={{ height: `${Math.max(18, (item.value / max) * 150)}px` }} /><span className="py-2 text-xs font-black text-slate-600">{new Date(item.date).getUTCFullYear()}</span></div>)}
      </div></div>
      <p className="mt-3 text-xs leading-5 text-slate-500">Exact annual counts are shown above each bar. Latest comparable Census vintage: {new Date(latest.date).getUTCFullYear()}.</p>
    </div>;
  }
  return <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5 text-sm text-slate-600">No observations are available yet.</div>;
}

function GuidanceStep({ number: stepNumber, label, text, icon: Icon }: { number: number; label: string; text: string; icon: typeof Play }) {
  return <div className="flex gap-3 rounded-xl border border-slate-200 bg-white p-3">
    <span className="relative grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-[#e8f0f7] text-[#245b87]"><Icon className="h-4.5 w-4.5" aria-hidden="true" /><span className="absolute -right-1.5 -top-1.5 grid h-5 w-5 place-items-center rounded-full bg-[#245b87] text-[10px] font-black text-white">{stepNumber}</span></span>
    <div><p className="font-black text-slate-950">{label}</p><p className="mt-0.5 text-xs leading-5 text-slate-600">{text}</p></div>
  </div>;
}

function ActionCard({ icon: Icon, title, text, to, accent = false }: { icon: typeof Users; title: string; text: string; to: string; accent?: boolean }) {
  return <Link to={to} className={`group flex min-h-36 flex-col rounded-2xl border p-5 outline-none transition focus-visible:ring-4 ${accent ? 'border-[#d7a315] bg-[#f7c43c] text-slate-950 hover:bg-[#f4bb22] focus-visible:ring-amber-200' : 'border-slate-200 bg-white text-slate-950 hover:border-[#245b87] focus-visible:ring-sky-200'}`}>
    <Icon className={`h-6 w-6 ${accent ? 'text-slate-900' : 'text-[#245b87]'}`} aria-hidden="true" />
    <span className="mt-3 font-black">{title}</span><span className={`mt-1 text-sm leading-5 ${accent ? 'text-slate-800' : 'text-slate-600'}`}>{text}</span>
    <span className="mt-auto pt-3 text-sm font-black">Start <ArrowRight className="inline h-4 w-4 transition group-hover:translate-x-0.5" aria-hidden="true" /></span>
  </Link>;
}

export default function IssueDetailPage() {
  const { slug = 'housing-rent' } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { hash } = location;
  const [data, setData] = useState<State | null>(null);
  const [showAllVideos, setShowAllVideos] = useState(false);
  const [showAllBills, setShowAllBills] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    setData(null);
    setError('');
    setShowAllVideos(false);
    setShowAllBills(false);
    fetchIssueDetail(slug).then((result) => active && setData(result)).catch((reason) => active && setError(reason.message));
    return () => { active = false; };
  }, [slug]);

  useEffect(() => {
    if (!data || !hash) return;
    document.getElementById(hash.slice(1))?.scrollIntoView({ block: 'start' });
  }, [data, hash]);

  if (error) return <main className="min-h-screen bg-[#edede9] px-6 py-16 text-slate-950"><div className="mx-auto max-w-3xl rounded-2xl border border-slate-200 bg-white p-8"><h1 className="text-3xl font-black">Issue guide</h1><p className="mt-3 text-slate-600">We could not load this issue right now. Please try again. Your other pages are still available.</p></div></main>;
  if (!data) return <main className="min-h-screen bg-[#edede9] p-16 text-center text-slate-600">Loading sourced issue data…</main>;

  const leadSeries = ISSUE_TRENDS[slug] || data.evidence.find((series) => series.observations.length > 1) || data.evidence[0];
  const issueName = data.summary.title;
  const issueLower = issueName.toLowerCase();
  const selectedVideoId = new URLSearchParams(location.search).get('video');
  const selectedVideo = data.videos.find((video) => video.video_id === selectedVideoId) || null;
  const openVideo = (video: IssueVideo) => {
    const params = new URLSearchParams(location.search); params.set('video', video.video_id);
    navigate({ pathname: location.pathname, search: params.toString(), hash: location.hash });
  };
  const closeVideo = () => {
    const params = new URLSearchParams(location.search); params.delete('video');
    navigate({ pathname: location.pathname, search: params.toString(), hash: location.hash }, { replace: true });
  };
  const updateVideo = (next: IssueVideo) => setData((current) => current ? { ...current, videos: current.videos.map((item) => item.video_id === next.video_id ? next : item) } : current);

  return <main id="main-content" className="min-h-screen bg-[#edede9] pb-40 text-slate-950 md:pb-28">
    <header className="bg-[#245b87] px-5 py-6 text-white md:py-9">
      <div className="mx-auto max-w-4xl">
        <Link to="/agenda" className="inline-flex min-h-11 items-center gap-1 text-sm font-bold text-sky-50"><ArrowLeft className="h-4 w-4" />Agenda</Link>
        <p className="mt-1 text-xs font-bold uppercase tracking-[.16em] text-sky-100">Issue guide</p>
        <h1 className="mt-1 text-4xl font-black tracking-tight md:text-5xl">{issueName}</h1>
        <p className="mt-3 max-w-2xl text-base leading-7 text-sky-50">{data.summary.summary || `Facts, perspectives, legislation, and ways to act on ${issueLower}.`}</p>
      </div>
    </header>

    <div className="mx-auto max-w-4xl space-y-12 px-4 py-6 sm:px-6 md:py-10">
      <section id="evidence" aria-labelledby="facts-heading" className="scroll-mt-24 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
        <div className="flex items-start gap-3"><span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#e8f0f7] text-[#245b87]"><TrendingUp className="h-5 w-5" aria-hidden="true" /></span><div><p className="text-xs font-black uppercase tracking-[.16em] text-[#245b87]">Step 1 · Understand the data</p><h2 id="facts-heading" className="mt-1 text-2xl font-black">{issueName} facts &amp; trends</h2><p className="mt-2 text-sm leading-6 text-slate-600">Start with the numbers. Every measure includes its date and original source.</p></div></div>
        {!data.availability.evidence && <p className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">Sourced data is temporarily unavailable. You can still watch videos, review legislation, and act below.</p>}
        {data.availability.evidence && !leadSeries && <p className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">No sourced measures are connected yet. Continue below for reviewed videos, official bills, and actions.</p>}
        {leadSeries && <article className="mt-6"><h3 className="text-xl font-black text-slate-950">{leadSeries.title}</h3><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">{evidenceExplanation(leadSeries, issueName)}</p><div className="mt-4"><EvidenceVisual series={leadSeries} /></div><div className="mt-3"><SourceLink source={leadSeries.source} /></div></article>}
      </section>

      <section id="watch" aria-labelledby="watch-heading" className="scroll-mt-24">
        <div className="flex items-start gap-3"><span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#e8f0f7] text-[#245b87]"><Play className="h-5 w-5" aria-hidden="true" /></span><div><p className="text-xs font-black uppercase tracking-[.16em] text-[#245b87]">Step 2 · Learn and discuss</p><h2 id="watch-heading" className="mt-1 text-2xl font-black">Watch and discuss {issueLower}</h2><p className="mt-2 text-sm leading-6 text-slate-600">Use each video to understand a perspective, examine its claims, and join the conversation attached to that video.</p></div></div>
        <div aria-label="How to use these videos" className="mt-5 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          <GuidanceStep number={1} icon={Play} label="Watch" text="Hear the argument and note its sources." />
          <GuidanceStep number={2} icon={Search} label="Think" text="Ask what is supported, missing, or disputed." />
          <GuidanceStep number={3} icon={MessageCircle} label="Comment" text="Ask questions and respond on the video page." />
          <GuidanceStep number={4} icon={Users} label="Act" text="Contact officials or follow a bill." />
        </div>
        {!data.availability.videos ? <p className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">Videos are temporarily unavailable. You can still review legislation and take action below.</p>
          : data.videos.length === 0 ? <p className="mt-5 rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600">No reviewed videos are connected to {issueLower} yet. Continue below for official bills and actions.</p>
            : <><div className="mt-5 grid gap-4 md:grid-cols-3">{data.videos.slice(0, showAllVideos ? data.videos.length : 3).map((video) => <button type="button" key={video.video_id} className="group overflow-hidden rounded-2xl border border-slate-200 bg-white text-left shadow-sm outline-none transition hover:border-[#245b87] focus-visible:ring-4 focus-visible:ring-sky-200" onClick={() => openVideo(video)} aria-label={`Watch and discuss: ${video.caption}`}>
              {videoThumbnail(video) ? <img src={videoThumbnail(video)!} alt="" className="aspect-video w-full bg-slate-200 object-cover" loading="lazy" /> : <span aria-hidden="true" className="grid aspect-video w-full place-items-center bg-slate-200 text-[#245b87]"><Play className="h-10 w-10" /></span>}
              <span className="block p-4"><span className="block text-[11px] font-black uppercase tracking-[.14em] text-[#245b87]">{video.content_origin === 'community' ? 'Shared by a community member' : 'Reviewed source'}</span><span className="mt-2 block text-base font-black leading-6 text-slate-950 group-hover:text-[#164d78]">{video.caption}</span><span className="mt-2 block text-sm text-slate-600">{video.creator_label}</span><span className="mt-3 block text-sm font-bold text-[#164d78]">Watch and comment <ArrowRight className="inline h-4 w-4" /></span></span>
            </button>)}</div>
            {data.videos.length > 3 && <button type="button" aria-expanded={showAllVideos} className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-3 font-bold text-[#164d78] outline-none hover:bg-slate-50 focus-visible:ring-4 focus-visible:ring-sky-200" onClick={() => setShowAllVideos((current) => !current)}>{showAllVideos ? <><ChevronUp className="h-5 w-5" />Show fewer videos</> : <><ChevronDown className="h-5 w-5" />Show {data.videos.length - 3} more videos</>}</button>}
            {data.videoTotal > data.videos.length && <p className="mt-3 text-sm text-slate-600">Showing {data.videos.length} recent videos from {data.videoTotal} connected to {issueLower}.</p>}</>}
      </section>

      {slug === 'jobs-unemployment' && <section id="federal-jobs" className="scroll-mt-24"><div className="flex items-center gap-3"><Users className="text-[#245b87]" /><h2 className="text-2xl font-black">Federal jobs now open</h2></div>{!data.availability.federalJobs && <p className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">USAJOBS is temporarily unavailable.</p>}{data.availability.federalJobs && <><p className="mt-2 text-sm text-slate-600">{data.federalJobTotal.toLocaleString()} current USAJOBS listings. Showing {data.federalJobs.length} official listings.</p><div className="mt-5 grid gap-4 md:grid-cols-2">{data.federalJobs.map((job) => <article key={`${job.url}-${job.position_title}`} className="rounded-2xl border border-slate-200 bg-white p-5"><p className="text-xs font-bold uppercase tracking-wider text-[#245b87]">{job.organization_name || job.department_name}</p><h3 className="mt-2 text-lg font-black">{job.position_title}</h3><p className="mt-2 text-sm text-slate-600">{job.location || 'Location listed on USAJOBS'}{job.schedule_type ? ` · ${job.schedule_type}` : ''}</p><a className="mt-4 inline-flex min-h-11 items-center text-sm font-bold text-[#164d78] hover:underline" href={job.url} target="_blank" rel="noreferrer">View official listing <ExternalLink className="ml-1 h-4 w-4" /></a></article>)}</div>{data.federalJobsSource && <div className="mt-3"><SourceLink source={data.federalJobsSource} /></div>}</>}</section>}

      <section id="legislation" aria-labelledby="legislation-heading" className="scroll-mt-24">
        <div className="flex items-start gap-3"><span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#e8f0f7] text-[#245b87]"><Landmark className="h-5 w-5" aria-hidden="true" /></span><div><p className="text-xs font-black uppercase tracking-[.16em] text-[#245b87]">Step 3 · Follow the decisions</p><h2 id="legislation-heading" className="mt-1 text-2xl font-black">{issueName} legislation</h2><p className="mt-2 text-sm leading-6 text-slate-600">See what each bill addresses, where it stands, and its latest official action before deciding what you think.</p></div></div>
        {!data.availability.bills && <p className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">Legislation is temporarily unavailable. You can still contact representatives or prepare to vote below.</p>}
        {data.availability.bills && data.bills.length === 0 && <p className="mt-5 rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600">No official bills are connected yet. You can still contact representatives or prepare to vote below.</p>}
        <div className="mt-5 space-y-4">{data.bills.slice(0, showAllBills ? data.bills.length : 3).map((bill) => <article key={bill.bill_id} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <div className="flex flex-col justify-between gap-3 sm:flex-row"><div><p className="text-xs font-black uppercase tracking-[.12em] text-[#245b87]">{bill.bill_type.toUpperCase()} {bill.bill_number} · {bill.congress}th Congress</p><h3 className="mt-2 text-xl font-black text-slate-950">{bill.title || bill.bill_id}</h3></div><span className="h-fit w-fit shrink-0 rounded-full bg-[#e8f0f7] px-3 py-1 text-xs font-black text-[#164d78]">{phaseLabel[bill.phase]}</span></div>
          <div className="mt-4 rounded-xl border border-sky-100 bg-[#f3f8fc] p-4"><p className="text-xs font-black uppercase tracking-[.12em] text-[#245b87]">What this bill would do</p>{bill.summary_text ? <p className="mt-2 line-clamp-4 text-sm leading-6 text-slate-800">{bill.summary_text.replace(/^AI-generated summary \(no CRS summary published yet\):\s*/i, '')}</p> : <p className="mt-2 text-sm leading-6 text-slate-600">A trustworthy plain-language summary is not available yet. Open the bill to review its official text and details.</p>}<p className="mt-2 text-[11px] font-bold text-slate-500">{bill.summary_source === 'crs' ? 'Official Congressional Research Service summary' : 'No summary added—WeThePeople will not guess'}</p></div>
          <details className="mt-3 rounded-xl border border-slate-200 bg-white px-4 py-3"><summary className="cursor-pointer text-sm font-black text-[#164d78]">Status and official details</summary>{bill.relevance_note && <div className="mt-3"><p className="text-xs font-black uppercase tracking-[.12em] text-slate-500">Why it appears here</p><p className="mt-1 text-sm leading-6 text-slate-700">{bill.relevance_note}</p></div>}{bill.latest_action_text && <div className="mt-3"><p className="text-xs font-black uppercase tracking-[.12em] text-slate-500">Latest official action{bill.latest_action_date ? ` · ${date(bill.latest_action_date)}` : ''}</p><p className="mt-1 text-sm leading-6 text-slate-700">{bill.latest_action_text}</p></div>}</details>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3"><SourceLink source={bill.source} /><Link className="inline-flex min-h-10 items-center gap-1 rounded-lg bg-[#245b87] px-4 text-sm font-black text-white outline-none hover:bg-[#164d78] focus-visible:ring-4 focus-visible:ring-sky-200" to={`/politics/bill/${bill.bill_id}`}>View bill <FileText className="h-4 w-4" /></Link></div>
        </article>)}</div>
        {data.bills.length > 3 && <button type="button" aria-expanded={showAllBills} className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-3 font-bold text-[#164d78] outline-none hover:bg-slate-50 focus-visible:ring-4 focus-visible:ring-sky-200" onClick={() => setShowAllBills((current) => !current)}>{showAllBills ? <><ChevronUp className="h-5 w-5" />Show fewer bills</> : <><ChevronDown className="h-5 w-5" />Show {data.bills.length - 3} more bills</>}</button>}
        {data.billTotal > data.bills.length && <p className="mt-3 text-sm text-slate-600">Showing {data.bills.length} recent bills from {data.billTotal} connected through the official Congress.gov policy area. Relevance is not an endorsement.</p>}
      </section>

      <section aria-labelledby="action-heading" className="rounded-3xl border border-slate-200 bg-slate-100 p-5 sm:p-7">
        <p className="text-xs font-black uppercase tracking-[.16em] text-[#245b87]">Step 4 · Choose an action</p><h2 id="action-heading" className="mt-1 text-2xl font-black">Take action on {issueLower}</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">Choose one specific task. Each option opens the tool you selected and keeps this issue in context.</p>
        <div className="mt-5 grid gap-3 md:grid-cols-3"><ActionCard icon={Users} title="Contact your representatives" text={`Find your officials and decide how to contact them about ${issueLower}.`} to={`/politics/find-rep?issue=${encodeURIComponent(slug)}`} accent /><ActionCard icon={Landmark} title="Review the legislation" text="Return to the bills above and choose one to examine in detail." to={`/issues/${slug}#legislation`} /><ActionCard icon={Vote} title="Prepare to vote" text="Check your ballot and polling information before the next election." to={`/act?target_type=issue&target_id=${encodeURIComponent(slug)}#act-option-vote`} /></div>
      </section>
    </div>
    {selectedVideo && <IssueVideoDialog video={selectedVideo} returnPath={`${location.pathname}?video=${encodeURIComponent(selectedVideo.video_id)}`} onClose={closeVideo} onChange={updateVideo} />}
  </main>;
}
