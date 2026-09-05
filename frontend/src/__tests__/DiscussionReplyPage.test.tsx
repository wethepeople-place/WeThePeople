import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';

import DiscussionReplyPage from '../pages/DiscussionReplyPage';

afterEach(() => vi.unstubAllGlobals());

it('shows a focused composer and returns to the feed after posting', async () => {
  vi.stubGlobal('fetch', vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ id: 7, body: 'Original civic post', author: { id: 2, display_name: 'Alex' }, replies: [], attachments: [], reply_total: 0 }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ id: 12, post_id: 7, moderation_status: 'published' }) }));
  render(<MemoryRouter initialEntries={['/discuss', '/discuss/7/reply']} initialIndex={1}><Routes>
    <Route path="/discuss" element={<h1>Discussions feed</h1>} />
    <Route path="/discuss/:postId/reply" element={<DiscussionReplyPage />} />
  </Routes></MemoryRouter>);

  expect(await screen.findByText('Original civic post')).toBeTruthy();
  fireEvent.change(screen.getByRole('textbox', { name: 'Post your reply' }), { target: { value: 'My quick reply' } });
  fireEvent.click(screen.getByRole('button', { name: 'Post' }));
  expect(await screen.findByRole('heading', { name: 'Discussions feed' })).toBeTruthy();
});
