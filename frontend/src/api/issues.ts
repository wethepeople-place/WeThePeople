import { getApiBaseUrl } from './client';

export type IssueSource = { url: string; publisher: string; retrieved_at: string };
export type IssueSummary = {
  slug: string; title: string; summary: string | null;
  evidence_series_count: number; bill_count: number;
};
export type AgendaIssue = {
  rank: number; slug: string; title: string; summary: string | null;
  evidence_note: string | null; evidence_series_count: number; bill_count: number;
  latest_evidence_date: string | null; priority_share: number; priority_note: string;
  community_score: null;
};
export type IssueAgenda = {
  total: number;
  methodology: {
    kind: 'public_priorities_poll'; label: string; description: string;
    community_ranked: false; sample_size: number; survey_start: string; survey_end: string;
    margin_of_error_points: number; source_url: string; publisher: string;
    question: string; tie_break: string; updated_at: string | null;
  };
  items: AgendaIssue[];
};
export type EvidenceObservation = {
  date: string; value: number; source_record_id: string | null; source: IssueSource;
};
export type EvidenceSeries = {
  key: string; title: string; unit: string;
  geography: { type: string; id: string };
  source: IssueSource; observations: EvidenceObservation[];
};
export type IssueBill = {
  bill_id: string; congress: number; bill_type: string; bill_number: number;
  title: string | null; policy_area: string | null;
  phase: 'past' | 'current' | 'upcoming' | 'enacted'; status_bucket: string | null;
  status_reason: string | null; latest_action_text: string | null;
  latest_action_date: string | null; relevance_note: string | null; source: IssueSource;
};
export type IssueVideo = {
  video_id: string; content_origin: 'reviewed' | 'community'; caption: string; creator_label: string;
  delivery?: { provider: string | null; provider_video_id: string | null; poster_url: string | null } | null;
  issue: { slug: string; title: string };
};
export type FederalJob = {
  position_title: string; organization_name: string; department_name: string;
  salary_min: string; salary_max: string; location: string; grade: string;
  schedule_type: string; start_date: string; end_date: string; url: string;
};

async function read<T>(path: string): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`);
  if (!response.ok) throw new Error(response.status === 404 ? 'Issue not found' : 'Issue data is unavailable');
  return response.json() as Promise<T>;
}

export function fetchIssueAgenda() {
  return read<IssueAgenda>('/issues');
}

export async function fetchIssueDetail(slug: string) {
  const safeSlug = encodeURIComponent(slug);
  const summary = await read<IssueSummary>(`/issues/${safeSlug}`);
  const [evidence, bills, feed, federalJobs] = await Promise.all([
    read<{ issue_slug: string; total: number; series: EvidenceSeries[] }>(`/issues/${safeSlug}/evidence`).then((value) => ({ value, available: true })).catch(() => ({ value: { series: [] as EvidenceSeries[] }, available: false })),
    read<{ issue_slug: string; total: number; bills: IssueBill[] }>(`/issues/${safeSlug}/bills`).then((value) => ({ value, available: true })).catch(() => ({ value: { total: 0, bills: [] as IssueBill[] }, available: false })),
    read<{ total: number; videos: IssueVideo[] }>(`/videos?limit=25&issue_slug=${safeSlug}`).then((value) => ({ value, available: true })).catch(() => ({ value: { total: 0, videos: [] as IssueVideo[] }, available: false })),
    slug === 'jobs-unemployment'
      ? read<{ total: number; jobs: FederalJob[]; source: IssueSource }>(`/issues/${safeSlug}/federal-jobs`).then((value) => ({ value, available: true })).catch(() => ({ value: { total: 0, jobs: [] as FederalJob[], source: null }, available: false }))
      : Promise.resolve({ value: { total: 0, jobs: [] as FederalJob[], source: null }, available: true }),
  ]);
  return {
    summary,
    evidence: evidence.value.series,
    bills: bills.value.bills,
    billTotal: bills.value.total || bills.value.bills.length,
    videos: feed.value.videos,
    videoTotal: feed.value.total,
    federalJobs: federalJobs.value.jobs,
    federalJobTotal: federalJobs.value.total,
    federalJobsSource: federalJobs.value.source,
    availability: { evidence: evidence.available, bills: bills.available, videos: feed.available, federalJobs: federalJobs.available },
  };
}
