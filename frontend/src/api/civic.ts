import { getApiBaseUrl } from './client';

const BASE = getApiBaseUrl();

async function apiFetch<T>(path: string, options?: { method?: string; body?: unknown; params?: Record<string, string | number> }): Promise<T> {
  // BASE can be a relative path like "/api" (prod, same-origin) or an absolute
  // URL like "https://api.wethepeopleforus.com" (local dev with VITE_API_BASE_URL).
  // `new URL("/api/...")` without a base throws "Invalid URL" — that's the
  // "failed to construct URL" error users were hitting on /civic/verify.
  // Fix: pass window.location.origin as the base so relative paths resolve.
  const raw = `${BASE}${path}`;
  const origin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost';
  const url = new URL(raw, origin);
  if (options?.params) {
    Object.entries(options.params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, String(v));
    });
  }
  const res = await fetch(url.toString(), {
    method: options?.method || 'GET',
    headers: {
      'Content-Type': 'application/json',
      ...(localStorage.getItem('wtp_access_token') ? { Authorization: `Bearer ${localStorage.getItem('wtp_access_token')}` } : {}),
    },
    ...(options?.body ? { body: JSON.stringify(options.body) } : {}),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

// ── Promises ──

export interface PromiseItem {
  id: number;
  person_id: string;
  person_name: string;
  title: string;
  description: string;
  source_url: string;
  promise_date: string | null;
  category: string;
  status: string;
  retire_reason: string | null;
  progress: number;
  confidence_score: number | null;
  hot_score: number | null;
  linked_bill_ids: string[];
  linked_action_ids: number[];
  milestones: MilestoneItem[];
  created_at: string;
}

export interface MilestoneItem {
  id: number;
  title: string;
  description: string;
  evidence_url: string;
  status: string;
  achieved_date: string | null;
}

export function fetchPromises(params: Record<string, string | number> = {}) {
  return apiFetch<{ total: number; items: PromiseItem[] }>('/civic/promises', { params });
}

export function fetchPromise(id: number) {
  return apiFetch<PromiseItem>(`/civic/promises/${id}`);
}

export function createPromise(data: {
  person_id: string; person_name?: string; title: string; description?: string;
  source_url?: string; promise_date?: string; category?: string;
}) {
  return apiFetch<PromiseItem>('/civic/promises', { method: 'POST', body: data });
}

// ── Proposals ──

export interface ProposalItem {
  id: number;
  title: string;
  body: string;
  category: string;
  sector: string;
  status: string;
  upvotes: number;
  downvotes: number;
  confidence_score: number | null;
  hot_score: number | null;
  published_at: string | null;
  created_at: string;
}

export function fetchProposals(params: Record<string, string | number> = {}) {
  return apiFetch<{ total: number; items: ProposalItem[] }>('/civic/proposals', { params });
}

export function createProposal(data: { title: string; body: string; category?: string; sector?: string }) {
  return apiFetch<{ id: number }>('/civic/proposals', { method: 'POST', body: data });
}

// ── Voting ──

export function castVote(targetType: string, targetId: number, value: 1 | -1) {
  return apiFetch<{ action: string; value?: number }>('/civic/vote', { method: 'POST', body: { target_type: targetType, target_id: targetId, value } });
}

export interface CitizenSolution {
  id: number;
  creator_user_id: number;
  creator_display_name: string;
  issue_slug: string;
  title: string;
  summary: string;
  body?: string;
  status: string;
  latest_revision_number: number;
  vote_totals: { support: number; oppose: number; total_ballots: number };
  current_user_choice: 'support' | 'oppose' | null;
  vote_rule: string;
  vote_choices: Array<'support' | 'oppose'>;
  created_at: string;
  updated_at: string;
  discussion_post_id: number | null;
  duplicate_of_solution_id?: number | null;
  message?: string;
}

export function fetchSolutions(issueSlug: string) {
  return apiFetch<{ total: number; limit: number; offset: number; items: CitizenSolution[] }>('/solutions', { params: { issue_slug: issueSlug } });
}

export function createCitizenSolution(data: { issue_slug: string; title: string; summary: string; body: string }) {
  return apiFetch<CitizenSolution>('/solutions', { method: 'POST', body: data });
}

export function setSolutionVote(solutionId: number, choice: 'support' | 'oppose' | null) {
  return apiFetch<{ current_user_choice: 'support' | 'oppose' | null; vote_totals: CitizenSolution['vote_totals']; vote_rule: string }>(`/solutions/${solutionId}/vote`, { method: 'PUT', body: { choice } });
}

export function fetchSolution(issueSlug: string, solutionId: number) {
  return apiFetch<CitizenSolution>(`/solutions/${solutionId}`, { params: { issue_slug: issueSlug } });
}

export interface SolutionRevisionItem {
  revision_number: number; title: string; summary: string; body: string;
  change_note: string; created_at: string; editor_display_name: string;
}

export function fetchSolutionRevisions(solutionId: number) {
  return apiFetch<{ solution_id: number; latest_revision_number: number; items: SolutionRevisionItem[] }>(`/solutions/${solutionId}/revisions`);
}

export function reviseSolution(solutionId: number, data: { title: string; summary: string; body: string; change_note: string }) {
  return apiFetch<CitizenSolution>(`/solutions/${solutionId}`, { method: 'PUT', body: data });
}

export interface PublicDiscussionDetail {
  id: number; body: string; author: { display_name: string }; created_at: string;
  replies: Array<{ id: number; body: string; author: { display_name: string }; created_at: string }>;
  attachments: Array<{ type: string; reference_id: string; label: string | null }>;
}

export function fetchPublicDiscussion(postId: number) {
  return apiFetch<PublicDiscussionDetail>(`/discussions/${postId}`);
}

// ── Badges ──

export interface BadgeItem {
  slug: string;
  name: string;
  description: string;
  icon: string;
  category: string;
  threshold: number;
  level: number;
}

export interface UserBadgeItem {
  badge_slug: string;
  badge_name: string;
  badge_icon: string;
  badge_category: string;
  earned_at: string;
  progress_count: number;
}

export function fetchBadges() {
  return apiFetch<{ total: number; items: BadgeItem[] }>('/civic/badges');
}

export function fetchMyBadges() {
  return apiFetch<{ total: number; items: UserBadgeItem[] }>('/civic/badges/mine');
}

// ── Verification ──

export function fetchVerificationStatus() {
  return apiFetch<{ level: number; level_label: string; verified_zip: string | null; verified_state: string | null }>('/civic/verification');
}

export function verifyResidence(zipCode: string) {
  return apiFetch<{ level: number; state: string; zip: string; message: string }>('/civic/verify/residence', { method: 'POST', body: { zip_code: zipCode } });
}

