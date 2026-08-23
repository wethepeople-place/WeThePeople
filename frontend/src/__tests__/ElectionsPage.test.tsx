import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';

import ElectionsPage from '../pages/ElectionsPage';

afterEach(() => vi.unstubAllGlobals());

it('performs a private election lookup and renders the official civic answer', async () => {
  vi.stubGlobal('fetch', vi.fn().mockImplementation((input: string) => Promise.resolve({
    ok: true,
    json: async () => input.endsWith('/elections') ? { items: [] } : {
      election: { id: '9', name: 'General Election', election_day: '2026-11-03' }, mail_only: false,
      polling_locations: [{ name: 'Community Center', address: { line1: '10 Civic Way', city: 'Town', state: 'MD', zip: '20000' }, polling_hours: '7 a.m. to 8 p.m.', start_date: null, end_date: null, notes: null, sources: [] }],
      early_vote_sites: [], drop_off_locations: [],
      contests: [{ type: 'General', office: 'Mayor', district: null, candidates: [{ name: 'Alex Example', party: 'Independent', candidate_url: null }], referendum_url: null, sources: [] }],
      election_authorities: [{ region: 'Maryland', name: 'State Board', election_info_url: 'https://example.gov', registration_url: null, registration_status_url: null, voting_location_url: null, ballot_info_url: null }],
      privacy: { address_retained: false, registration_status_collected: false, ballot_choices_collected: false },
    },
  })));
  render(<MemoryRouter><ElectionsPage /></MemoryRouter>);
  const addressInput = screen.getByLabelText('Full registered residential address') as HTMLInputElement;
  fireEvent.change(addressInput, { target: { value: '123 Private Road, Town, MD 20000' } });
  fireEvent.click(screen.getByRole('button', { name: 'Find my election' }));
  expect(await screen.findByRole('heading', { name: 'General Election' })).toBeTruthy();
  expect(screen.getByText('Community Center')).toBeTruthy();
  expect(screen.getByText('Alex Example')).toBeTruthy();
  expect(addressInput.value).toBe('');
  await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/elections/lookup'), expect.objectContaining({ method: 'POST' })));
});

it('explains that a ZIP code alone cannot identify a ballot without sending it', async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ items: [] }) });
  vi.stubGlobal('fetch', fetchMock);
  render(<MemoryRouter><ElectionsPage /></MemoryRouter>);
  const addressInput = screen.getByLabelText('Full registered residential address') as HTMLInputElement;
  fireEvent.change(addressInput, { target: { value: '21136' } });
  fireEvent.click(screen.getByRole('button', { name: 'Find my election' }));
  expect((await screen.findByRole('alert')).textContent).toContain('A ZIP code alone cannot identify your ballot.');
  expect(addressInput.value).toBe('21136');
  expect(fetchMock).toHaveBeenCalledTimes(1);
});
