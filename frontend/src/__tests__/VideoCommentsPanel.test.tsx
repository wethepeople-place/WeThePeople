import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';

import VideoCommentsPanel from '../components/VideoCommentsPanel';

vi.mock('../contexts/AuthContext', () => ({ useAuth: () => ({ isAuthenticated: true }) }));

afterEach(() => vi.unstubAllGlobals());

it('keeps the panel open and refreshes after a video comment is submitted', async () => {
  const onClose = vi.fn();
  vi.stubGlobal('fetch', vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ total: 0, limit: 20, offset: 0, items: [] }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ id: 14, moderation_status: 'pending', message: 'Submitted for moderation' }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ total: 0, limit: 20, offset: 0, items: [] }) }));

  const { container } = render(<MemoryRouter><VideoCommentsPanel videoId="community-42" videoCaption="Housing video" open onClose={onClose} /></MemoryRouter>);

  expect(container.firstElementChild?.className).toContain('z-[80]');
  expect(container.querySelector('footer')?.className).toContain('safe-area-inset-bottom');

  const comment = await screen.findByRole('textbox', { name: 'Add a comment' });
  fireEvent.change(comment, { target: { value: 'A useful reply.' } });
  fireEvent.click(screen.getByRole('button', { name: 'Submit comment for review' }));

  await waitFor(() => expect(vi.mocked(fetch)).toHaveBeenCalledTimes(3));
  expect(onClose).not.toHaveBeenCalled();
  expect(screen.getByRole('dialog', { name: 'Comments for Housing video' })).toBeTruthy();
  expect((comment as HTMLTextAreaElement).value).toBe('');
  expect(vi.mocked(fetch).mock.calls[1][1]).toMatchObject({ method: 'POST' });
});

it('keeps the panel open and refreshes the thread after a reply is posted', async () => {
  const onClose = vi.fn();
  const post = {
    id: 7,
    body: 'Original comment',
    author: { id: 1, display_name: 'Alice' },
    moderation_status: 'published',
    reply_count: 0,
    created_at: '2026-11-11T00:00:00Z',
    updated_at: '2026-11-11T00:00:00Z',
    attachments: [],
    reactions: { like: 0, insightful: 0, disagree: 0 },
    viewer_reactions: [],
    viewer_bookmarked: false,
  };
  vi.stubGlobal('fetch', vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ total: 1, limit: 20, offset: 0, items: [post] }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ id: 8, post_id: 7, moderation_status: 'published' }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ ...post, reply_count: 1, reply_total: 1, replies: [{ id: 8, parent_reply_id: null, body: 'New reply', author: { id: 2, display_name: 'Bob' }, created_at: '2026-11-11T00:01:00Z' }] }) }));

  render(<MemoryRouter><VideoCommentsPanel videoId="community-42" videoCaption="Housing video" open onClose={onClose} /></MemoryRouter>);

  fireEvent.click(await screen.findByRole('button', { name: 'Reply' }));
  const reply = screen.getByRole('textbox', { name: 'Reply to Alice' });
  fireEvent.change(reply, { target: { value: 'New reply' } });
  fireEvent.click(screen.getByRole('button', { name: 'Post reply' }));

  expect(await screen.findByText('New reply')).toBeTruthy();
  expect(onClose).not.toHaveBeenCalled();
  expect(screen.getByRole('dialog', { name: 'Comments for Housing video' })).toBeTruthy();
  expect(vi.mocked(fetch).mock.calls[1][1]).toMatchObject({ method: 'POST' });
});
