import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';

import AgendaPage from '../pages/AgendaPage';

afterEach(() => vi.unstubAllGlobals());

it('renders the honest initial agenda from reviewed issue data', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      total: 1,
      methodology: { kind: 'initial_evidence_catalog', label: 'Initial agenda', description: 'Ordered by published source coverage, not community popularity.', community_ranked: false, updated_at: '2026-08-17T00:00:00Z' },
      items: [{ rank: 1, slug: 'housing-rent', title: 'Housing & Rent', summary: 'Housing evidence.', evidence_note: 'Median rent: 2014 dollars (2024-01-01)', evidence_series_count: 2, bill_count: 7, latest_evidence_date: '2024-01-01', community_score: null }],
    }),
  }));
  render(<MemoryRouter><AgendaPage /></MemoryRouter>);
  expect(await screen.findByRole('heading', { name: 'Housing & Rent' })).toBeTruthy();
  expect(screen.getByText('Ordered by published source coverage, not community popularity.')).toBeTruthy();
  expect(screen.getByText('Community score pending genuine participation')).toBeTruthy();
  expect(screen.getByRole('link', { name: /Housing & Rent/ }).getAttribute('href')).toBe('/issues/housing-rent');
  expect(screen.getByRole('link', { name: 'Propose an issue' }).getAttribute('href')).toBe('/discuss?compose=1#composer');
  expect(screen.queryByText(/214,508/)).toBeNull();
});
