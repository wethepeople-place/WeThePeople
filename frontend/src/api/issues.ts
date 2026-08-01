import { getApiBaseUrl } from './client';

export type IssueSource = { url: string; publisher: string; retrieved_at: string };
export type IssueSummary = {
  slug: string; title: string; summary: string | null;
  evidence_series_count: number; bill_count: number;
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
  phase: 'past' | 'current' | 'upcoming'; status_bucket: string | null;
  status_reason: string | null; latest_action_text: string | null;
  latest_action_date: string | null; relevance_note: string | null; source: IssueSource;
};

async function read<T>(path: string): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`);
  if (!response.ok) throw new Error(response.status === 404 ? 'Issue not found' : 'Issue data is unavailable');
  return response.json() as Promise<T>;
}

export async function fetchIssueDetail(slug: string) {
  const safeSlug = encodeURIComponent(slug);
  const [summary, evidence, bills] = await Promise.all([
    read<IssueSummary>(`/issues/${safeSlug}`),
    read<{ issue_slug: string; total: number; series: EvidenceSeries[] }>(`/issues/${safeSlug}/evidence`),
    read<{ issue_slug: string; total: number; bills: IssueBill[] }>(`/issues/${safeSlug}/bills`),
  ]);
  return { summary, evidence: evidence.series, bills: bills.bills };
}
