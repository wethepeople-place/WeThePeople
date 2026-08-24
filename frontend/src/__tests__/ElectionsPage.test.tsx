import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';

import ElectionsPage from '../pages/ElectionsPage';

afterEach(() => vi.unstubAllGlobals());

const catalogAvailability = { status: 'available', fetched_at: '2026-08-24T07:00:00Z', refresh_after: '2026-08-24T07:15:00Z' };

it('performs a private election lookup and renders the official civic answer', async () => {
  vi.stubGlobal('fetch', vi.fn().mockImplementation((input: string) => Promise.resolve({
    ok: true,
    json: async () => input.endsWith('/elections') ? { availability: catalogAvailability, source: { name: 'Google Civic Information API', official_only: true }, items: [{ id: '9', name: 'Maryland General Election', election_day: '2026-11-03', division_id: 'ocd-division/country:us/state:md' }] } : {
      election: { id: '9', name: 'General Election', election_day: '2026-11-03' }, mail_only: false,
      polling_locations: [{ name: 'Community Center', address: { line1: '10 Civic Way', city: 'Town', state: 'MD', zip: '20000' }, polling_hours: '7 a.m. to 8 p.m.', start_date: null, end_date: null, notes: null, sources: [] }],
      early_vote_sites: [], drop_off_locations: [],
      contests: [{ type: 'General', office: 'Mayor', district: null, candidates: [{ name: 'Alex Example', party: 'Independent', candidate_url: null }], referendum_url: null, sources: [] }],
      election_authorities: [{ region: 'Maryland', name: 'State Board', election_info_url: 'https://example.gov', registration_url: null, registration_status_url: null, voting_location_url: null, ballot_info_url: null }],
      privacy: { address_retained: false, registration_status_collected: false, ballot_choices_collected: false },
    },
  })));
  render(<MemoryRouter><ElectionsPage /></MemoryRouter>);
  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
  fireEvent.change(screen.getByLabelText('State or District of Columbia'), { target: { value: 'MD' } });
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
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ availability: catalogAvailability, source: { name: 'Google Civic Information API', official_only: true }, items: [{ id: '9', name: 'Maryland General Election', election_day: '2026-11-03', division_id: 'ocd-division/country:us/state:md' }] }) });
  vi.stubGlobal('fetch', fetchMock);
  render(<MemoryRouter><ElectionsPage /></MemoryRouter>);
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
  fireEvent.change(screen.getByLabelText('State or District of Columbia'), { target: { value: 'MD' } });
  const addressInput = screen.getByLabelText('Full registered residential address') as HTMLInputElement;
  fireEvent.change(addressInput, { target: { value: '21136' } });
  fireEvent.click(screen.getByRole('button', { name: 'Find my election' }));
  expect((await screen.findByRole('alert')).textContent).toContain('A ZIP code alone cannot identify your ballot.');
  expect(addressInput.value).toBe('21136');
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

it('does not request an address when the selected state has no supported election', async () => {
  // The availability field is intentionally absent to prove the Pages-first
  // frontend remains compatible with the currently deployed API contract.
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ items: [
    { id: '2000', name: 'VIP Test Election', election_day: '2031-12-06', division_id: 'ocd-division/country:us' },
    { id: '12', name: 'Delaware Primary Election', election_day: '2026-09-15', division_id: 'ocd-division/country:us/state:de' },
  ] }) });
  vi.stubGlobal('fetch', fetchMock);
  render(<MemoryRouter><ElectionsPage /></MemoryRouter>);
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
  expect(screen.queryByText('VIP Test Election')).toBeNull();
  fireEvent.change(screen.getByLabelText('State or District of Columbia'), { target: { value: 'MD' } });
  expect((await screen.findByRole('status')).textContent).toContain('not currently publishing election data for Maryland');
  expect(screen.queryByLabelText('Full registered residential address')).toBeNull();
  expect(screen.getByRole('link', { name: /Official Maryland voting information/ }).getAttribute('href')).toBe('https://vote.gov/register/maryland');
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

it('distinguishes provider unavailable from state not covered and never requests an address', async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: false, status: 503, statusText: 'Service Unavailable',
    json: async () => ({ detail: 'Election provider is temporarily unavailable. Coverage could not be checked.' }),
  });
  vi.stubGlobal('fetch', fetchMock);
  render(<MemoryRouter><ElectionsPage /></MemoryRouter>);
  expect((await screen.findByRole('alert')).textContent).toContain('This does not mean your state has no election.');
  fireEvent.change(screen.getByLabelText('State or District of Columbia'), { target: { value: 'MD' } });
  expect(screen.queryByLabelText('Full registered residential address')).toBeNull();
  expect(screen.getByText(/Coverage cannot be checked/)).toBeTruthy();
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

it('labels cached election coverage as stale while keeping supported lookup available', async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({
    availability: { ...catalogAvailability, status: 'stale' },
    source: { name: 'Google Civic Information API', official_only: true },
    items: [{ id: '12', name: 'Delaware Primary Election', election_day: '2026-09-15', division_id: 'ocd-division/country:us/state:de' }],
  }) });
  vi.stubGlobal('fetch', fetchMock);
  render(<MemoryRouter><ElectionsPage /></MemoryRouter>);
  expect((await screen.findByRole('status')).textContent).toContain('Using the most recent available election catalog.');
  fireEvent.change(screen.getByLabelText('State or District of Columbia'), { target: { value: 'DE' } });
  expect(screen.getByLabelText('Full registered residential address')).toBeTruthy();
  expect(fetchMock).toHaveBeenCalledTimes(1);
});
