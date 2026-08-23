import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';

import AgendaPage from '../pages/AgendaPage';

afterEach(() => vi.unstubAllGlobals());

it('renders the sourced public-priorities agenda and expands all 20 issues', async () => {
  const items = Array.from({ length: 20 }, (_, index) => ({
    rank: index + 1,
    slug: index === 0 ? 'immigration' : index === 5 ? 'housing-rent' : `issue-${index + 1}`,
    title: index === 0 ? 'Immigration' : index === 5 ? 'Housing & Rent' : `Issue ${index + 1}`,
    summary: 'A sourced public priority.', evidence_note: null, evidence_series_count: 0, bill_count: 0,
    latest_evidence_date: null, priority_share: Math.max(7, 44 - index * 2),
    priority_note: `${Math.max(7, 44 - index * 2)}% named this as a 2026 government priority`, community_score: null,
  }));
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      total: 20,
      methodology: { kind: 'public_priorities_poll', label: '2026 public priorities', description: 'Ranked by a national poll.', community_ranked: false, sample_size: 1146, survey_start: '2025-12-04', survey_end: '2025-12-08', margin_of_error_points: 4, source_url: 'https://apnorc.org/example', publisher: 'AP-NORC', question: 'Name up to five.', tie_break: 'Published category order.', updated_at: '2025-12-08' },
      items,
    }),
  }));
  render(<MemoryRouter><AgendaPage /></MemoryRouter>);
  expect(await screen.findByRole('heading', { name: 'Immigration' })).toBeTruthy();
  expect(screen.getByText(/1,146 U.S. adults/)).toBeTruthy();
  expect(screen.getByText(/Respondents could name up to five priorities/)).toBeTruthy();
  expect(screen.queryByRole('heading', { name: 'Housing & Rent' })).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Show 15 more issues' }));
  expect(screen.getByRole('heading', { name: 'Housing & Rent' })).toBeTruthy();
  expect(screen.getByRole('link', { name: /Housing & Rent/ }).getAttribute('href')).toBe('/issues/housing-rent');
  expect(screen.getByRole('link', { name: 'Propose an issue' }).getAttribute('href')).toBe('/discuss?compose=1#composer');
  expect(screen.getByRole('link', { name: /View AP-NORC source/ }).getAttribute('href')).toBe('https://apnorc.org/example');
  expect(screen.queryByText(/214,508/)).toBeNull();
});
