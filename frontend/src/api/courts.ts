import { getApiBaseUrl } from './client';

export interface CourtSource { url: string; publisher: string; retrieved_at: string }
export interface CourtCaseItem {
  case_id: string; case_name: string; court_name: string; jurisdiction: string;
  docket_number: string; filed_date: string; procedural_status: string;
  disposition: string | null; docket_url: string; last_verified_at: string; source: CourtSource;
}
export interface CourtCaseDetail extends CourtCaseItem {
  parties: Array<{ name: string; role: string; entity_type: string | null; entity_id: string | null }>;
  events: Array<{ id: number; event_date: string; event_type: string; assertion_kind: string; summary: string; document_url: string | null; source: CourtSource }>;
}

async function read<T>(path: string): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`);
  if (!response.ok) throw new Error(response.status === 404 ? 'Court case not found' : `Unable to load court records (${response.status})`);
  return response.json();
}

export function fetchCourtCases(issueSlug?: string, billId?: string) {
  const params = new URLSearchParams();
  if (issueSlug) params.set('issue_slug', issueSlug);
  if (billId) params.set('bill_id', billId);
  const query = params.size ? `?${params.toString()}` : '';
  return read<{ total: number; limit: number; offset: number; items: CourtCaseItem[] }>(`/courts${query}`);
}

export function fetchCourtCase(caseId: string) {
  return read<CourtCaseDetail>(`/courts/${encodeURIComponent(caseId)}`);
}
