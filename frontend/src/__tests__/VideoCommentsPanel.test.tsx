import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';

import VideoCommentsPanel from '../components/VideoCommentsPanel';

vi.mock('../contexts/AuthContext', () => ({ useAuth: () => ({ isAuthenticated: true }) }));

afterEach(() => vi.unstubAllGlobals());

it('closes after a video comment is submitted and leaves the video in place', async () => {
  const onClose = vi.fn();
  vi.stubGlobal('fetch', vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ total: 0, limit: 20, offset: 0, items: [] }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ id: 14, moderation_status: 'pending', message: 'Submitted for moderation' }) }));

  render(<MemoryRouter><VideoCommentsPanel videoId="community-42" videoCaption="Housing video" open onClose={onClose} /></MemoryRouter>);

  const comment = await screen.findByRole('textbox', { name: 'Add a comment' });
  fireEvent.change(comment, { target: { value: 'A useful reply.' } });
  fireEvent.click(screen.getByRole('button', { name: 'Submit comment for review' }));

  await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1));
  expect(vi.mocked(fetch).mock.calls[1][1]).toMatchObject({ method: 'POST' });
});
