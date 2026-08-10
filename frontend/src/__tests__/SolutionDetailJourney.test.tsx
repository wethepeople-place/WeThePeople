import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import SolutionDetailPage from '../pages/SolutionDetailPage';

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: null, isAuthenticated: false }),
}));

afterEach(() => vi.unstubAllGlobals());

it('continues from a citizen solution into discussion, evidence, legal context, and representative action', async () => {
  vi.stubGlobal('fetch', vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({
      id: 42,
      creator_user_id: 2,
      creator_display_name: 'Civic neighbor',
      issue_slug: 'housing-rent',
      title: 'Expand housing supply near transit',
      summary: 'A reviewed community proposal.',
      body: 'Proposal details and tradeoffs.',
      status: 'published',
      latest_revision_number: 1,
      vote_totals: { support: 3, oppose: 1, total_ballots: 4 },
      current_user_choice: null,
      vote_rule: 'Participating users only.',
      vote_choices: ['support', 'oppose'],
      created_at: '2026-08-09T00:00:00Z',
      updated_at: '2026-08-09T00:00:00Z',
      discussion_post_id: 7,
    }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ solution_id: 42, latest_revision_number: 1, items: [] }) }));

  render(<MemoryRouter initialEntries={['/issues/housing-rent/solutions/42']}><Routes><Route path="/issues/:slug/solutions/:solutionId" element={<SolutionDetailPage />} /></Routes></MemoryRouter>);

  await waitFor(() => expect(screen.getByRole('heading', { name: 'Expand housing supply near transit' })).toBeTruthy());
  expect(screen.getByRole('link', { name: 'Open citizen discussion' }).getAttribute('href')).toBe('/discuss/7');
  expect(screen.getByRole('link', { name: 'Return to official evidence' }).getAttribute('href')).toBe('/issues/housing-rent');
  expect(screen.getByRole('link', { name: 'Government activity' }).getAttribute('href')).toBe('/government');
  expect(screen.getByRole('link', { name: 'Related court proceedings' }).getAttribute('href')).toBe('/courts?issue=housing-rent');
  expect(screen.getByRole('link', { name: 'Contact your representatives' }).getAttribute('href')).toBe('/politics/find-rep?issue=housing-rent');
});
