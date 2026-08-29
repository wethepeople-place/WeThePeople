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

  it('settles an empty public feed and points people to its composer', async () => {
    render(<MemoryRouter><DiscussionsPage /></MemoryRouter>);
    await waitFor(() => expect(screen.getByText('No posts here yet')).toBeTruthy());
    expect(screen.queryByLabelText('Loading latest discussions')).toBeNull();
    expect(screen.getByRole('link', { name: 'Create a post' }).getAttribute('href')).toBe('/discuss?compose=1#composer');
    expect(screen.getByText('Latest').getAttribute('aria-current')).toBe('page');
  });

  it('requests and preserves issue context', async () => {
    render(<MemoryRouter initialEntries={['/discuss?issue=housing-rent']}><DiscussionsPage /></MemoryRouter>);
    await waitFor(() => expect(screen.getByText('No posts here yet')).toBeTruthy());
    expect(vi.mocked(fetch).mock.calls[0][0].toString()).toContain('issue_slug=housing-rent');
    expect(screen.getByRole('link', { name: 'Return to official issue evidence' }).getAttribute('href')).toBe('/issues/housing-rent');
  });

  it('offers a text-first composer and automatically suggests an Agenda issue for social links', async () => {
    authenticated = true;
    vi.mocked(fetch)
      .mockResolvedValueOnce({ ok: true, json: async () => ({ total: 0, limit: 20, offset: 0, items: [] }) } as Response)
      .mockResolvedValueOnce({ ok: true, json: async () => ({ total: 1, methodology: {}, items: [{ rank: 1, slug: 'housing-rent', title: 'Housing & Rent' }] }) } as Response);
    render(<MemoryRouter><DiscussionsPage /></MemoryRouter>);
    fireEvent.click(screen.getByRole('button', { name: 'What do you want people to know?' }));
    await waitFor(() => expect(screen.getByText('Write a post, share a link, or do both.')).toBeTruthy());
    const message = screen.getByLabelText('What do you want people to know?');
    expect(screen.getByRole('button', { name: 'Post' }).hasAttribute('disabled')).toBe(true);
    fireEvent.change(message, { target: { value: 'A text-only civic post' } });
    expect(screen.getByRole('button', { name: 'Post' }).hasAttribute('disabled')).toBe(false);
    fireEvent.click(screen.getByRole('button', { name: 'Add link' }));
    const link = screen.getByLabelText(/Link/);
    expect(link.getAttribute('placeholder')).toBe('https://…');
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
    fireEvent.click(screen.getByRole('button', { name: 'Change' }));
    expect(await screen.findByRole('option', { name: 'Housing & Rent' })).toBeTruthy();
    vi.mocked(fetch).mockResolvedValueOnce({ ok: true, json: async () => ({
      id: 10, moderation_status: 'published', message: 'Posted',
    }) } as Response);
    fireEvent.click(screen.getByRole('button', { name: 'Post' }));
    expect(await screen.findByText('Posted. It is now visible in Latest discussions.')).toBeTruthy();
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
    await waitFor(() => expect(screen.getByText('What should Congress do next?')).toBeTruthy());
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

  it('recognizes a supported provider URL pasted directly into the main composer', async () => {
    authenticated = true;
    vi.mocked(fetch)
      .mockResolvedValueOnce({ ok: true, json: async () => ({ total: 0, limit: 20, offset: 0, items: [] }) } as Response)
      .mockResolvedValueOnce({ ok: true, json: async () => ({ total: 1, methodology: {}, items: [{ rank: 1, slug: 'housing-rent', title: 'Housing & Rent' }] }) } as Response);
    render(<MemoryRouter><DiscussionsPage /></MemoryRouter>);
    fireEvent.click(screen.getByRole('button', { name: 'What do you want people to know?' }));
    const message = await screen.findByLabelText('What do you want people to know?');
    vi.mocked(fetch).mockResolvedValueOnce({ ok: true, json: async () => ({
      provider: 'tiktok', canonical_url: 'https://www.tiktok.com/@person/video/7579560442230508831',
      suggested_issue: { slug: 'housing-rent', title: 'Housing & Rent', score: 6 },
      alternatives: [], confidence: 'high', metadata_available: true,
    }) } as Response);
    fireEvent.change(message, { target: { value: 'https://www.tiktok.com/@person/video/7579560442230508831?tracking=1' } });
    await waitFor(() => expect(screen.getByText('Suggested issue')).toBeTruthy(), { timeout: 2000 });
    vi.mocked(fetch).mockResolvedValueOnce({ ok: true, json: async () => ({ id: 11, moderation_status: 'published', message: 'Posted' }) } as Response);
    fireEvent.click(screen.getByRole('button', { name: 'Post' }));
    expect(await screen.findByText('Posted. It is now visible in Latest discussions.')).toBeTruthy();
    const [, request] = vi.mocked(fetch).mock.calls.at(-1) || [];
    const payload = JSON.parse(String(request?.body));
    expect(payload.video_url).toContain('tiktok.com/@person/video/7579560442230508831');
    expect(payload.body).toBe('');
  });

  it('renders ordinary HTTPS links as safe external links', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ total: 1, limit: 20, offset: 0, items: [{
        id: 9, body: 'Read the public record\n\nhttps://example.gov/public-record',
        author: { id: 2, display_name: 'Civic neighbor' }, moderation_status: 'published', reply_count: 0,
        created_at: '2026-08-29T00:00:00Z', updated_at: '2026-08-29T00:00:00Z', attachments: [],
        reactions: { like: 0, insightful: 0, disagree: 0 }, viewer_reactions: [], viewer_bookmarked: false,
      }] }),
    } as Response);
    render(<MemoryRouter><DiscussionsPage /></MemoryRouter>);
    const externalLink = await screen.findByRole('link', { name: /https:\/\/example.gov\/public-record/ });
    expect(externalLink.getAttribute('href')).toBe('https://example.gov/public-record');
    expect(externalLink.getAttribute('target')).toBe('_blank');
  });
});
