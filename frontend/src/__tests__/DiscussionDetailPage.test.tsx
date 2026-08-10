import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import DiscussionDetailPage from '../pages/DiscussionDetailPage';

afterEach(() => vi.unstubAllGlobals());

it('derives evidence, solution, and related context links from attachments', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      id: 7,
      body: 'What should government do next?',
      author: { display_name: 'Civic neighbor' },
      created_at: '2026-08-09T00:00:00Z',
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
});
