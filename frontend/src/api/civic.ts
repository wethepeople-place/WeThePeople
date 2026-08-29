import { getApiBaseUrl } from './client';

const BASE = getApiBaseUrl();

async function apiFetch<T>(path: string, options?: { method?: string; body?: unknown; params?: Record<string, string | number> }): Promise<T> {
  // BASE can be a relative path like "/api" (prod, same-origin) or an absolute
  // URL like "https://api.wethepeople.place" (local dev with VITE_API_BASE_URL).
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

// ── Civic forecasts (non-monetary) ──

export interface ForecastMarket {
  id: number;
  market_type: 'bill' | 'election';
  subject_id: string;
  question: string;
  options: Array<{ key: string; label: string; party?: string | null; responses: number | null; share: number | null }>;
  status: 'open' | 'locked' | 'resolved' | 'void';
  closes_at: string;
  source_url: string;
  response_count: number | null;
  privacy_threshold: number;
  current_user_choice: string | null;
  resolved_option: string | null;
  resolution_source_url: string | null;
  resolution_reason: string | null;
  resolved_at: string | null;
  rules: string;
}

export function fetchOpenForecasts(marketType?: 'bill' | 'election') {
  const query = marketType ? `?market_type=${marketType}` : '';
  return apiFetch<{ items: ForecastMarket[]; privacy_threshold: number }>(`/forecasts${query}`);
}

export function fetchBillForecast(billId: string) {
  return apiFetch<ForecastMarket>(`/forecasts/bills/${encodeURIComponent(billId)}`);
}

export function setBillForecast(billId: string, optionKey: string) {
  return apiFetch<ForecastMarket>(`/forecasts/bills/${encodeURIComponent(billId)}`, { method: 'PUT', body: { option_key: optionKey } });
}

export function setElectionForecast(contestToken: string, optionKey: string) {
  return apiFetch<ForecastMarket>('/forecasts/elections', { method: 'PUT', body: { contest_token: contestToken, option_key: optionKey } });
}

export function fetchElectionForecast(contestToken: string) {
  return apiFetch<ForecastMarket>('/forecasts/elections/market', { method: 'POST', body: { contest_token: contestToken } });
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
  video_link?: DiscussionVideoLink | null;
  duplicate_of_solution_id?: number | null;
  message?: string;
}

export function fetchSolutions(issueSlug: string) {
  return apiFetch<{ total: number; limit: number; offset: number; items: CitizenSolution[] }>('/solutions', { params: { issue_slug: issueSlug } });
}

export function createCitizenSolution(data: { issue_slug: string; title: string; summary: string; body: string; video_url?: string | null }) {
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
  id: number; body: string; author: { id: number | null; display_name: string; is_demo?: boolean }; created_at: string;
  reply_count: number; reply_total: number;
  replies: Array<{ id: number; parent_reply_id: number | null; body: string; author: { id: number | null; display_name: string; is_demo?: boolean }; created_at: string }>;
  attachments: Array<{
    type: 'video' | 'issue' | 'bill' | 'politician' | 'solution' | 'source';
    reference_id: string;
    label: string | null;
    source?: { url: string; publisher: string } | null;
  }>;
  video_link?: DiscussionVideoLink | null;
}

export interface DiscussionVideoLink {
  provider: 'youtube' | 'tiktok' | 'facebook' | 'instagram'; provider_video_id: string; canonical_url: string;
}

export interface PublicDiscussionPost {
  id: number;
  body: string;
  author: { id: number | null; display_name: string; is_demo?: boolean };
  moderation_status: 'published';
  reply_count: number;
  created_at: string;
  updated_at: string;
  attachments: Array<{
    type: 'video' | 'issue' | 'bill' | 'politician' | 'solution' | 'source';
    reference_id: string;
    label: string | null;
    source?: { url: string; publisher: string } | null;
  }>;
  video_link?: DiscussionVideoLink | null;
  reactions: Record<'like' | 'insightful' | 'disagree', number>;
  viewer_reactions: Array<'like' | 'insightful' | 'disagree'>;
  viewer_bookmarked: boolean;
}

export function fetchPublicDiscussions(issueSlug?: string, videoId?: string, offset = 0, limit = 20) {
  return apiFetch<{ total: number; limit: number; offset: number; items: PublicDiscussionPost[] }>('/discussions', { params: { ...(issueSlug ? { issue_slug: issueSlug } : {}), ...(videoId ? { video_id: videoId } : {}), offset, limit } });
}

export type DiscussionContinuation = {
  reviewed_videos: Array<{
    video_id: string; creator_label: string; caption: string; transcript: string | null;
    delivery: { provider: string | null; provider_video_id: string | null; canonical_url: string } | null;
    source: { url: string; publisher: string }; issue: { slug: string; title: string };
  }>;
  agenda: Array<{ slug: string; title: string; summary: string | null; priority_note: string; bill_count: number }>;
  bills: Array<{ bill_id: string; title: string | null; latest_action_text: string | null; latest_action_date: string | null }>;
  bill_total: number;
};

export function fetchDiscussionContinuation() {
  return apiFetch<DiscussionContinuation>('/discussions/continuation');
}

export function fetchPublicDiscussion(postId: number) {
  return apiFetch<PublicDiscussionDetail>(`/discussions/${postId}`);
}

export function createDiscussion(data: { body: string; video_url?: string; issue_slug?: string }) {
  return apiFetch<{ id: number; moderation_status: 'pending' | 'published'; message: string }>('/discussions', { method: 'POST', body: data });
}

export interface DiscussionLinkSuggestion {
  provider: 'youtube' | 'tiktok' | 'facebook' | 'instagram';
  canonical_url: string;
  suggested_issue: { slug: string; title: string; score: number } | null;
  alternatives: Array<{ slug: string; title: string; score: number }>;
  confidence: 'low' | 'medium' | 'high';
  metadata_available: boolean;
}

export function suggestDiscussionIssue(videoUrl: string) {
  return apiFetch<DiscussionLinkSuggestion>('/discussions/link-suggestion', {
    method: 'POST', body: { video_url: videoUrl },
  });
}

export function fetchVideoComments(videoId: string) {
  return apiFetch<{ total: number; limit: number; offset: number; items: PublicDiscussionPost[] }>(`/discussions/videos/${encodeURIComponent(videoId)}`);
}

export function createVideoComment(videoId: string, body: string) {
  return apiFetch<{ id: number; moderation_status: 'pending'; message: string }>(`/discussions/videos/${encodeURIComponent(videoId)}/comments`, { method: 'POST', body: { body } });
}

export function createDiscussionReply(postId: number, body: string, parentReplyId?: number) {
  return apiFetch<{ id: number; post_id: number; moderation_status: 'published' }>(`/discussions/${postId}/replies`, {
    method: 'POST',
    body: { body, ...(parentReplyId ? { parent_reply_id: parentReplyId } : {}) },
  });
}

export interface RepresentativeActOptions {
  representative: { person_id: string; display_name: string; chamber: string; state: string; party: string };
  contacts: Array<{
    id: number; office_type: 'washington' | 'district' | 'state' | 'contact_form'; label: string;
    phone: string | null; contact_url: string | null; address: string | null;
    source: { publisher: string; url: string }; verification_status: 'verified';
    retrieved_at: string; verified_at: string;
  }>;
  fallback: { label: string; phone: string; source: { publisher: string; url: string } };
  message_policy: { auto_send: false; delivery_claimed: false; instructions: string };
}

export function fetchRepresentativeActOptions(personId: string) {
  return apiFetch<RepresentativeActOptions>(`/act/representatives/${encodeURIComponent(personId)}`);
}

export function saveActReceipt(data: {
  idempotency_key: string;
  action_kind: 'call' | 'message' | 'follow' | 'event' | 'petition' | 'circle' | 'public_comment';
  target_type: 'video' | 'discussion' | 'issue' | 'bill' | 'vote' | 'representative' | 'solution' | 'activity' | 'circle';
  target_id: string;
  representative_id?: string;
  status: 'prepared' | 'opened' | 'user_confirmed_submitted' | 'response_received' | 'attended' | 'completed' | 'cancelled';
  private_note?: string;
  allow_aggregate?: boolean;
}) {
  return apiFetch<{ id: number; status: string; allow_aggregate: boolean }>(`/act/receipts/${encodeURIComponent(data.idempotency_key)}`, { method: 'PUT', body: data });
}

export interface PublicActionCircle {
  id: number; name: string; objective: string; description: string;
  target_type: string; target_id: string; geography: string | null;
  location_precision: string; membership_mode: 'open' | 'approval';
  conduct_rules: string; completion_condition: string;
  moderation_status: 'published' | 'completed'; member_count: number;
  viewer_membership_status: string | null; created_at: string;
}

export interface PublicCivicActivity {
  id: number; circle_id: number | null; title: string; description: string;
  host_type: 'official' | 'organization' | 'community'; format: 'in_person' | 'online' | 'hybrid';
  starts_at: string; ends_at: string | null; timezone: string;
  public_location: string | null; public_url: string | null;
  accessibility: string | null; capacity: number | null;
}

export function fetchActionCircles(targetType?: string, targetId?: string) {
  return apiFetch<{ items: PublicActionCircle[] }>('/act/circles', { params: {
    ...(targetType ? { target_type: targetType } : {}),
    ...(targetId ? { target_id: targetId } : {}),
  } });
}

export function joinActionCircle(circleId: number) {
  return apiFetch<{ status: 'active' | 'pending'; member_count_is_public: true; member_identity_is_public: false }>(`/act/circles/${circleId}/membership`, { method: 'PUT' });
}

export function fetchCivicActivities() {
  return apiFetch<{ items: PublicCivicActivity[] }>('/act/activities');
}

export function rsvpCivicActivity(activityId: number) {
  return apiFetch<{ status: 'going'; attendee_identity_is_public: false }>(`/act/activities/${activityId}/rsvp`, { method: 'PUT' });
}

export type ElectionLocation = {
  name: string | null;
  address: Record<string, string>;
  polling_hours: string | null;
  start_date: string | null;
  end_date: string | null;
  notes: string | null;
  sources: Array<{ name: string; official: boolean }>;
};

export type ElectionLookup = {
  election: { id: string; name: string; election_day: string | null };
  mail_only: boolean;
  polling_locations: ElectionLocation[];
  early_vote_sites: ElectionLocation[];
  drop_off_locations: ElectionLocation[];
  contests: Array<{
    type: string | null; office: string; district: string | null;
    candidates: Array<{ name: string; party: string | null; candidate_url: string | null; forecast_key: string }>;
    forecast_token: string | null;
    referendum_url: string | null;
    sources: Array<{ name: string; official: boolean }>;
  }>;
  election_authorities: Array<{
    region: string; name: string; election_info_url: string | null;
    registration_url: string | null; registration_status_url: string | null;
    voting_location_url: string | null; ballot_info_url: string | null;
  }>;
  privacy: { address_retained: false; registration_status_collected: false; ballot_choices_collected: false };
};

export function fetchUpcomingElections() {
  return apiFetch<{
    items: Array<{ id: string; name: string; election_day: string | null; division_id: string | null }>;
    availability?: { status: 'available' | 'stale'; fetched_at: string; refresh_after: string };
    source?: { name: string; official_only: true };
  }>('/elections');
}

export function lookupElectionInformation(address: string, electionId?: string) {
  return apiFetch<ElectionLookup>('/elections/lookup', {
    method: 'POST', body: { address, ...(electionId ? { election_id: electionId } : {}) },
  });
}

export type ActModerationItem = {
  kind: 'circle' | 'activity'; id: number; moderation_status: string;
  organizer: { display_name: string }; created_at: string; updated_at: string;
  name?: string; title?: string; objective?: string; description: string;
  target_type?: string; target_id?: string; geography?: string | null;
  membership_mode?: string; conduct_rules?: string; completion_condition?: string;
  circle_id?: number | null; host_type?: string; format?: string; starts_at?: string;
  ends_at?: string | null; timezone?: string; public_location?: string | null;
  public_url?: string | null; accessibility?: string | null; capacity?: number | null;
};

export function fetchActModerationQueue(status = 'pending') {
  return apiFetch<{ total: number; counts: { circles: number; activities: number }; items: ActModerationItem[] }>('/act/admin/moderation', { params: { status } });
}

export function moderateActItem(item: ActModerationItem, status: string, reason: string) {
  const collection = item.kind === 'circle' ? 'circles' : 'activities';
  return apiFetch<ActModerationItem>(`/act/admin/${collection}/${item.id}`, { method: 'PATCH', body: { status, reason } });
}

export type DiscussionReaction = 'like' | 'insightful' | 'disagree';

export function setDiscussionReaction(postId: number, reaction: DiscussionReaction, enabled: boolean) {
  return apiFetch<{ reaction: DiscussionReaction; enabled: boolean; reactions: PublicDiscussionPost['reactions'] }>(`/discussions/${postId}/reactions/${reaction}`, { method: enabled ? 'PUT' : 'DELETE' });
}

export function setDiscussionBookmark(postId: number, bookmarked: boolean) {
  return apiFetch<{ bookmarked: boolean }>(`/discussions/${postId}/bookmark`, { method: bookmarked ? 'PUT' : 'DELETE' });
}

export function reportDiscussionPost(postId: number, reason: string, details?: string) {
  return apiFetch<{ status: 'received' }>('/discussions/reports', { method: 'POST', body: { target_type: 'post', target_id: postId, reason, ...(details ? { details } : {}) } });
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

