import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import DiscussionsPage from '../pages/DiscussionsPage';

let authenticated = false;
vi.mock('../contexts/AuthContext', () => ({ useAuth: () => ({ isAuthenticated: authenticated }) }));

describe('DiscussionsPage', () => {
  beforeEach(() => {
    authenticated = false;
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ total: 0, limit: 20, offset: 0, items: [] }) }));
  });
  afterEach(() => vi.unstubAllGlobals());

  it('settles an empty public feed and links back into the journey', async () => {
    render(<MemoryRouter><DiscussionsPage /></MemoryRouter>);
    await waitFor(() => expect(screen.getByText('No published discussions yet')).toBeTruthy());
    expect(screen.queryByLabelText('Loading latest discussions')).toBeNull();
    expect(screen.getByRole('link', { name: 'Explore Watch' }).getAttribute('href')).toBe('/watch');
    expect(screen.getByText('Latest').getAttribute('aria-current')).toBe('page');
  });

  it('requests and preserves issue context', async () => {
    render(<MemoryRouter initialEntries={['/discuss?issue=housing-rent']}><DiscussionsPage /></MemoryRouter>);
    await waitFor(() => expect(screen.getByText('No published discussions yet')).toBeTruthy());
    expect(vi.mocked(fetch).mock.calls[0][0].toString()).toContain('issue_slug=housing-rent');
    expect(screen.getByRole('link', { name: 'Return to official issue evidence' }).getAttribute('href')).toBe('/issues/housing-rent');
  });

  it('puts the social link first and automatically suggests an Agenda issue', async () => {
    authenticated = true;
    vi.mocked(fetch)
      .mockResolvedValueOnce({ ok: true, json: async () => ({ total: 0, limit: 20, offset: 0, items: [] }) } as Response)
      .mockResolvedValueOnce({ ok: true, json: async () => ({ total: 1, methodology: {}, items: [{ rank: 1, slug: 'housing-rent', title: 'Housing & Rent' }] }) } as Response);
    render(<MemoryRouter><DiscussionsPage /></MemoryRouter>);
    await waitFor(() => expect(screen.getByText(/Paste a TikTok, Instagram, Facebook, or YouTube link/)).toBeTruthy());
    const link = screen.getByLabelText('Video link');
    expect(link.getAttribute('placeholder')).toBe('Paste link');
    expect(screen.queryByRole('combobox', { name: 'Agenda issue' })).toBeNull();
    expect(screen.queryByLabelText(/Your note/)).toBeNull();
    vi.mocked(fetch).mockResolvedValueOnce({ ok: true, json: async () => ({
      provider: 'tiktok', canonical_url: 'https://www.tiktok.com/@person/video/7679228789091519757',
      suggested_issue: { slug: 'housing-rent', title: 'Housing & Rent', score: 6 },
      alternatives: [], confidence: 'high', metadata_available: true,
    }) } as Response);
    fireEvent.change(link, { target: { value: 'https://www.tiktok.com/@person/video/7679228789091519757' } });
    await waitFor(() => expect(screen.getByText('Suggested issue')).toBeTruthy(), { timeout: 2000 });
    expect(screen.getByText('Housing & Rent')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Post' })).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Add a note' }));
    expect(screen.getByLabelText(/Your note/).hasAttribute('required')).toBe(false);
    fireEvent.click(screen.getByRole('button', { name: 'Change' }));
    expect(await screen.findByRole('option', { name: 'Housing & Rent' })).toBeTruthy();
  });

  it('renders a chronological civic post card with public counts', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ total: 1, limit: 20, offset: 0, items: [{
        id: 7, body: 'What should Congress do next?', author: { id: 2, display_name: 'Civic neighbor' },
        moderation_status: 'published', reply_count: 1, created_at: '2026-08-09T00:00:00Z', updated_at: '2026-08-09T00:00:00Z',
        attachments: [{ type: 'issue', reference_id: 'housing-rent', label: 'Housing & Rent evidence' }],
        reactions: { like: 2, insightful: 1, disagree: 0 }, viewer_reactions: [], viewer_bookmarked: false,
      }] }),
    } as Response);
    render(<MemoryRouter><DiscussionsPage /></MemoryRouter>);
    await waitFor(() => expect(screen.getByRole('link', { name: 'What should Congress do next?' }).getAttribute('href')).toBe('/discuss/7'));
    expect(screen.getByRole('link', { name: 'Housing & Rent evidence' }).getAttribute('href')).toBe('/issues/housing-rent');
    expect(screen.getByText('Civic neighbor')).toBeTruthy();
    expect(screen.getByRole('link', { name: '1 reply' }).getAttribute('href')).toBe('/discuss/7');
    expect(screen.getByRole('link', { name: 'Sign in to like' }).textContent).toContain('2');
  });

  it('labels server-identified synthetic records as a visual demo', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ total: 1, limit: 20, offset: 0, items: [{
        id: 8, body: 'Lorem ipsum. [Demo discussion]',
        author: { id: 9, display_name: 'Test User 01 (Demo)', is_demo: true },
        moderation_status: 'published', reply_count: 2, created_at: '2026-08-18T18:00:00Z', updated_at: '2026-08-18T18:00:00Z',
        attachments: [], reactions: { like: 1, insightful: 0, disagree: 0 }, viewer_reactions: [], viewer_bookmarked: false,
      }] }),
    } as Response);
    render(<MemoryRouter><DiscussionsPage /></MemoryRouter>);
    await waitFor(() => expect(screen.getByRole('note').textContent).toContain('not real civic participation'));
    expect(screen.getByText('Demo data')).toBeTruthy();
  });
});
