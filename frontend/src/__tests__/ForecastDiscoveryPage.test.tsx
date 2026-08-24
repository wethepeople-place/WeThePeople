import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';

import ForecastDiscoveryPage from '../pages/ForecastDiscoveryPage';

afterEach(() => vi.unstubAllGlobals());

it('lists open forecasts without exposing sub-threshold participation', async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ privacy_threshold: 5, items: [{
    id: 1, market_type: 'bill', subject_id: 'hr2725-119', question: 'Will H.R. 2725 become law?',
    options: [{ key: 'yes', label: 'Yes', responses: null, share: null }, { key: 'no', label: 'No', responses: null, share: null }],
    status: 'open', closes_at: '2027-01-03T00:00:00Z', source_url: 'https://www.congress.gov/bill/119th-congress/house-bill/2725',
    response_count: null, privacy_threshold: 5, current_user_choice: null, resolved_option: null, resolution_source_url: null, resolution_reason: null, resolved_at: null, rules: 'No money.',
  }] }) });
  vi.stubGlobal('fetch', fetchMock);
  render(<MemoryRouter><ForecastDiscoveryPage /></MemoryRouter>);
  expect(await screen.findByRole('heading', { name: 'Will H.R. 2725 become law?' })).toBeTruthy();
  expect(screen.getByText('Participation remains private until 5 responses.')).toBeTruthy();
  expect(screen.queryByText(/1 response/)).toBeNull();
  expect(screen.getByRole('link', { name: 'Open tracked bill' }).getAttribute('href')).toBe('/politics/bill/hr2725-119');

  fireEvent.click(screen.getByRole('button', { name: 'Elections' }));
  await waitFor(() => expect(fetchMock).toHaveBeenLastCalledWith(expect.stringContaining('/forecasts?market_type=election'), expect.anything()));
});
