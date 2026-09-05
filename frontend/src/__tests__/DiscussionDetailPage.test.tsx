import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import DiscussionDetailPage from '../pages/DiscussionDetailPage';

vi.mock('../contexts/AuthContext', () => ({ useAuth: () => ({ isAuthenticated: true }) }));

afterEach(() => vi.unstubAllGlobals());

it('derives evidence, solution, and related context links from attachments', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      id: 7,
      body: 'What should government do next?',
      author: { display_name: 'Civic neighbor' },
      created_at: '2026-08-09T00:00:00Z',
      reply_total: 0,
      replies: [],
      attachments: [
        { type: 'issue', reference_id: 'transit-access', label: 'Transit Access' },
        { type: 'solution', reference_id: '42', label: 'Transit proposal' },
        { type: 'bill', reference_id: 'hr8-119', label: 'H.R. 8' },
        { type: 'source', reference_id: '3', label: null, source: { url: 'https://www.congress.gov/bill/119th-congress/house-bill/8', publisher: 'Congress.gov' } },
      ],
    }),
  }));

  render(<MemoryRouter initialEntries={['/discuss/7']}><Routes><Route path="/discuss/:postId" element={<DiscussionDetailPage />} /></Routes></MemoryRouter>);

  await waitFor(() => expect(screen.getByRole('heading', { name: 'What should government do next?' })).toBeTruthy());
  expect(screen.getByRole('link', { name: 'Return to solution' }).getAttribute('href')).toBe('/issues/transit-access/solutions/42');
  expect(screen.getByRole('link', { name: 'Official evidence' }).getAttribute('href')).toBe('/issues/transit-access');
  expect(screen.getByRole('link', { name: 'H.R. 8' }).getAttribute('href')).toBe('/politics/bill/hr8-119');
  expect(screen.getByRole('link', { name: 'Congress.gov' }).getAttribute('href')).toContain('congress.gov');
  expect(screen.getByText('No replies yet. Be the first to join this conversation.')).toBeTruthy();
  expect(screen.getByRole('textbox', { name: 'Write a reply' })).toBeTruthy();
  expect(screen.getByRole('link', { name: 'Start a discussion' }).getAttribute('href')).toBe('/discuss?issue=transit-access&compose=1#composer');
  expect(screen.getByRole('link', { name: 'Propose a solution' }).getAttribute('href')).toBe('/discuss?issue=transit-access&compose=proposal#composer');
  expect(screen.getByRole('link', { name: 'Share link or video' }).getAttribute('href')).toBe('/discuss?issue=transit-access&compose=1#composer');
  expect(screen.getByRole('button', { name: /Image/ }).hasAttribute('disabled')).toBe(true);
});

it('posts a reply on the web and refreshes the conversation', async () => {
  const detail = (replies: Array<{ id: number; body: string; author: { display_name: string } }>) => ({
    id: 7, body: 'What should government do next?', author: { display_name: 'Civic neighbor' },
    created_at: '2026-08-09T00:00:00Z', reply_total: replies.length, replies, attachments: [],
  });
  vi.stubGlobal('fetch', vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => detail([]) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ id: 12, post_id: 7, moderation_status: 'published' }) })
    .mockResolvedValueOnce({ ok: true, json: async () => detail([{ id: 12, body: 'Evidence should guide the next step.', author: { display_name: 'You' } }]) }));

  render(<MemoryRouter initialEntries={['/discuss/7']}><Routes><Route path="/discuss/:postId" element={<DiscussionDetailPage />} /></Routes></MemoryRouter>);
  const reply = await screen.findByRole('textbox', { name: 'Write a reply' });
  fireEvent.change(reply, { target: { value: 'Evidence should guide the next step.' } });
  fireEvent.click(screen.getByRole('button', { name: 'Post reply' }));
  await waitFor(() => expect(screen.getByText('Evidence should guide the next step.')).toBeTruthy());
  expect(screen.getByRole('status').textContent).toBe('Reply posted.');
  expect(vi.mocked(fetch).mock.calls[1][1]).toMatchObject({ method: 'POST' });
});

it('returns to the previous screen after replying when opened from the app', async () => {
  vi.stubGlobal('fetch', vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({
      id: 7, body: 'What should government do next?', author: { display_name: 'Civic neighbor' },
      created_at: '2026-08-09T00:00:00Z', reply_total: 0, replies: [], attachments: [],
    }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ id: 12, post_id: 7, moderation_status: 'published' }) }));

  render(<MemoryRouter initialEntries={['/discuss', { pathname: '/discuss/7', state: { returnAfterReply: true } }]} initialIndex={1}><Routes>
    <Route path="/discuss" element={<h1>Discussions feed</h1>} />
    <Route path="/discuss/:postId" element={<DiscussionDetailPage />} />
  </Routes></MemoryRouter>);

  const reply = await screen.findByRole('textbox', { name: 'Write a reply' });
  fireEvent.change(reply, { target: { value: 'Return me to the feed.' } });
  fireEvent.click(screen.getByRole('button', { name: 'Post reply' }));

  expect(await screen.findByRole('heading', { name: 'Discussions feed' })).toBeTruthy();
  expect(vi.mocked(fetch)).toHaveBeenCalledTimes(2);
});
