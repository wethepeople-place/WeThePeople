import { afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import DiscussionPostCard from '../components/DiscussionPostCard';
import type { PublicDiscussionPost } from '../api/civic';

const item: PublicDiscussionPost = {
  id: 42, body: 'What evidence should Congress examine before the next vote?',
  author: { id: 3, display_name: 'Civic Neighbor' }, moderation_status: 'published', reply_count: 4,
  created_at: '2026-08-15T12:00:00Z', updated_at: '2026-08-15T12:00:00Z',
  attachments: [
    { type: 'issue', reference_id: 'housing-rent', label: 'Housing & Rent' },
    { type: 'video', reference_id: 'housing-video', label: 'Reviewed housing video' },
    { type: 'bill', reference_id: 'hr6644-119', label: 'H.R. 6644' },
    { type: 'source', reference_id: '9', label: 'Congress.gov source', source: { url: 'https://www.congress.gov/bill/119th-congress/house-bill/6644', publisher: 'Congress.gov' } },
  ],
  video_link: null, reactions: { like: 0, insightful: 2, disagree: 0 }, viewer_reactions: [], viewer_bookmarked: false,
};

describe('DiscussionPostCard', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('keeps standalone discussion cards simple and text-first', () => {
    render(<MemoryRouter initialEntries={['/discuss']}><DiscussionPostCard item={item} isAuthenticated={false} /></MemoryRouter>);
    expect(screen.queryByText('Published')).toBeNull();
    expect(screen.queryByText('Reviewed housing video')).toBeNull();
    expect(screen.queryByText('H.R. 6644')).toBeNull();
    expect(screen.getByRole('link', { name: 'About Housing & Rent' }).getAttribute('href')).toBe('/issues/housing-rent');
    expect(screen.getByRole('link', { name: '4 replies' }).getAttribute('href')).toBe('/discuss/42');
    expect(screen.getByRole('link', { name: 'Sign in to save privately' }).getAttribute('href')).toContain('next=%2Fdiscuss');
    expect(screen.queryByText('Demo data')).toBeNull();
  });

  it('shows a demo badge only from the server-issued flag', () => {
    render(<MemoryRouter><DiscussionPostCard item={{ ...item, author: { ...item.author, display_name: 'Ordinary name', is_demo: true } }} isAuthenticated={false} /></MemoryRouter>);
    expect(screen.getByText('Demo')).toBeTruthy();
  });

  it('updates reactions, private saves, and private reports honestly', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();
      if (url.includes('/reactions/like')) return { ok: true, json: async () => ({ reaction: 'like', enabled: true, reactions: { like: 1, insightful: 2, disagree: 0 } }) } as Response;
      if (url.includes('/bookmark')) return { ok: true, json: async () => ({ bookmarked: true }) } as Response;
      if (url.endsWith('/discussions/reports') && init?.method === 'POST') return { ok: true, json: async () => ({ status: 'received' }) } as Response;
      throw new Error(`Unexpected request: ${url}`);
    }));
    render(<MemoryRouter initialEntries={['/discuss']}><DiscussionPostCard item={item} isAuthenticated /></MemoryRouter>);
    fireEvent.click(screen.getByRole('button', { name: 'Like: 0' }));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Like: 1' }).getAttribute('aria-pressed')).toBe('true'));
    fireEvent.click(screen.getByRole('button', { name: 'Save privately' }));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Remove private save' }).getAttribute('aria-pressed')).toBe('true'));
    fireEvent.click(screen.getByRole('button', { name: 'Report' }));
    fireEvent.click(screen.getByRole('button', { name: 'Send private report' }));
    await waitFor(() => expect(screen.getByText('Report received privately for review.')).toBeTruthy());
  });
});
