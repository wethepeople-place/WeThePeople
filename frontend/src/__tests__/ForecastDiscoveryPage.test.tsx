import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';

import ForecastDiscoveryPage from '../pages/ForecastDiscoveryPage';

afterEach(() => vi.unstubAllGlobals());

it('lists open forecasts without exposing sub-threshold participation', async () => {
  const community = { privacy_threshold: 5, items: [{
    id: 1, market_type: 'bill', subject_id: 'hr2725-119', question: 'Will H.R. 2725 become law?',
    options: [{ key: 'yes', label: 'Yes', responses: null, share: null }, { key: 'no', label: 'No', responses: null, share: null }],
    status: 'open', closes_at: '2027-01-03T00:00:00Z', source_url: 'https://www.congress.gov/bill/119th-congress/house-bill/2725',
    response_count: null, privacy_threshold: 5, current_user_choice: null, resolved_option: null, resolution_source_url: null, resolution_reason: null, resolved_at: null, rules: 'No money.',
  }] };
  const external = { provider: 'polymarket', total: 1, items: [{
    id: 2, provider_market_id: 'pm-2', question: 'Will Candidate A win?',
    outcomes: [{ label: 'Yes', probability: 61 }, { label: 'No', probability: 39 }],
    volume: 5000, liquidity: 2000, closes_at: '2027-01-03T00:00:00Z',
    source_url: 'https://polymarket.com/event/candidate-a', observed_at: '2026-08-30T11:00:00Z',
    quality_score: 100, matched_market_id: null, label: 'Polymarket market-implied probability',
  }] };
  const fetchMock = vi.fn((url: string) => Promise.resolve({ ok: true, json: async () => url.includes('/forecasts/external') ? external : community }));
  vi.stubGlobal('fetch', fetchMock);
  render(<MemoryRouter><ForecastDiscoveryPage /></MemoryRouter>);
  expect(await screen.findByRole('heading', { name: 'Will H.R. 2725 become law?' })).toBeTruthy();
  expect(screen.getByText('Participation remains private until 5 responses.')).toBeTruthy();
  expect(screen.queryByText(/1 response/)).toBeNull();
  expect(screen.getByRole('link', { name: 'Open tracked bill' }).getAttribute('href')).toBe('/politics/bill/hr2725-119');
  expect(await screen.findByRole('heading', { name: 'Will Candidate A win?' })).toBeTruthy();
  expect(screen.getByText('61%')).toBeTruthy();

  fireEvent.click(screen.getByRole('button', { name: 'Elections' }));
  await waitFor(() => expect(fetchMock).toHaveBeenLastCalledWith(expect.stringContaining('/forecasts?market_type=election'), expect.anything()));
});
