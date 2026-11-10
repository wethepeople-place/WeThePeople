import { getApiBaseUrl } from './client';

const API_BASE = getApiBaseUrl();

export interface GuideAction {
  type: 'navigate' | 'search';
  path?: string;
  query?: string;
}

export interface GuideResponse {
  answer: string;
  action?: GuideAction | null;
  cached: boolean;
}

export async function askGuide(question: string, context: { page: string }): Promise<GuideResponse> {
  const response = await fetch(`${API_BASE}/guide/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, context }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || 'Your guide is temporarily unavailable.');
  return payload;
}

export async function getGuideRemaining(): Promise<{ remaining: number; limit: number }> {
  const response = await fetch(`${API_BASE}/guide/remaining`);
  if (!response.ok) throw new Error('Guide availability could not be checked.');
  return response.json();
}
