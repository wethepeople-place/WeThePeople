import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';

import ElectionsPage from '../pages/ElectionsPage';

afterEach(() => vi.unstubAllGlobals());

const catalogAvailability = { status: 'available', fetched_at: '2026-08-24T07:00:00Z', refresh_after: '2026-08-24T07:15:00Z' };
const source = { name: 'Google Civic Information API', url: 'https://developers.google.com/civic-information', kind: 'public_api' };
const marylandCatalog = { availability: catalogAvailability, source: { name: source.name, official_only: true }, items: [{ id: '9', name: 'Maryland General Election', election_day: '2026-11-03', division_id: 'ocd-division/country:us/state:md', description: null, registration_deadline: null, source }] };

it('performs a private election lookup and renders the official civic answer', async () => {
  vi.stubGlobal('fetch', vi.fn().mockImplementation((input: string) => Promise.resolve({
    ok: true,
    json: async () => input.includes('/elections?state=MD') ? marylandCatalog : {
      election: { id: '9', name: 'General Election', election_day: '2026-11-03' }, mail_only: false,
      polling_locations: [{ name: 'Community Center', address: { line1: '10 Civic Way', city: 'Town', state: 'MD', zip: '20000' }, polling_hours: '7 a.m. to 8 p.m.', start_date: null, end_date: null, notes: null, sources: [] }],
      early_vote_sites: [], drop_off_locations: [],
      contests: [{ type: 'General', office: 'Mayor', district: null, candidates: [{ name: 'Alex Example', party: 'Independent', candidate_url: null }], referendum_url: null, sources: [] }],
      election_authorities: [{ region: 'Maryland', name: 'State Board', election_info_url: 'https://example.gov', registration_url: null, registration_status_url: null, voting_location_url: null, ballot_info_url: null }],
      privacy: { address_retained: false, registration_status_collected: false, ballot_choices_collected: false },
    },
  })));
  render(<MemoryRouter><ElectionsPage /></MemoryRouter>);
  fireEvent.change(screen.getByLabelText('State or District of Columbia'), { target: { value: 'MD' } });
  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
  const zipInput = screen.getByLabelText('1. ZIP code') as HTMLInputElement;
  expect(screen.getByRole('link', { name: 'Google Civic Information API' }).getAttribute('href')).toBe('https://developers.google.com/civic-information');
  expect(screen.getByText('Election data last updated August 24, 2026.')).toBeTruthy();
  fireEvent.change(zipInput, { target: { value: '20000' } });
  const streetInput = screen.getByLabelText('2. House number and street') as HTMLInputElement;
  fireEvent.change(streetInput, { target: { value: '123 Private Road' } });
  fireEvent.click(screen.getByRole('button', { name: 'Find my election' }));
  expect(await screen.findByRole('heading', { name: 'General Election' })).toBeTruthy();
  expect(screen.getByText('Community Center')).toBeTruthy();
  expect(screen.getByText('Official hours: 7 a.m. to 8 p.m.')).toBeTruthy();
  expect(screen.getByText('What time should I come?')).toBeTruthy();
  expect(screen.getByText('What should I wear?')).toBeTruthy();
  expect(screen.getByText('What should I prepare?')).toBeTruthy();
  expect(screen.getByRole('link', { name: 'Drive directions to Community Center' }).getAttribute('href')).toContain('travelmode=driving');
  expect(screen.getByRole('link', { name: 'Transit directions to Community Center' }).getAttribute('href')).toContain('travelmode=transit');
  expect(screen.getByRole('link', { name: 'Request Uber to Community Center' }).getAttribute('href')).toContain('m.uber.com');
  expect(screen.getByRole('link', { name: 'Check the weather forecast' })).toBeTruthy();
  expect(screen.getByText('Alex Example')).toBeTruthy();
  expect(zipInput.value).toBe('');
  await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/elections/lookup'), expect.objectContaining({ method: 'POST' })));
});

it('asks for the house number and street only after a valid ZIP code', async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => marylandCatalog });
  vi.stubGlobal('fetch', fetchMock);
  render(<MemoryRouter><ElectionsPage /></MemoryRouter>);
  fireEvent.change(screen.getByLabelText('State or District of Columbia'), { target: { value: 'MD' } });
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
  const zipInput = screen.getByLabelText('1. ZIP code') as HTMLInputElement;
  expect(screen.queryByLabelText('2. House number and street')).toBeNull();
  fireEvent.change(zipInput, { target: { value: '21136' } });
  expect(screen.getByLabelText('2. House number and street')).toBeTruthy();
  expect(screen.getByText(/City and state are not requested again/)).toBeTruthy();
  expect(zipInput.value).toBe('21136');
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

it('offers official state links when exact local details are not published', async () => {
  const fetchMock = vi.fn().mockImplementation((input: string) => Promise.resolve(input.includes('/elections?state=MD') ? {
    ok: true, json: async () => marylandCatalog,
  } : {
    ok: false, status: 404, statusText: 'Not Found',
    json: async () => ({ detail: 'Exact ballot and polling-place details are not available from the provider for this address right now.' }),
  }));
  vi.stubGlobal('fetch', fetchMock);
  render(<MemoryRouter><ElectionsPage /></MemoryRouter>);
  fireEvent.change(screen.getByLabelText('State or District of Columbia'), { target: { value: 'MD' } });
  await screen.findByLabelText('1. ZIP code');
  fireEvent.change(screen.getByLabelText('1. ZIP code'), { target: { value: '21136' } });
  fireEvent.change(screen.getByLabelText('2. House number and street'), { target: { value: '126 Lamport Rd' } });
  fireEvent.click(screen.getByRole('button', { name: 'Find my election' }));
  const noticeHeading = await screen.findByText('Your official local details are not published here yet.');
  expect(noticeHeading).toBeTruthy();
  expect(screen.getByText('This does not mean there is no election.', { exact: false })).toBeTruthy();
  expect(screen.getByRole('button', { name: 'Continue with Maryland information' })).toBeTruthy();
  expect(screen.getAllByRole('link', { name: /Maryland voting rules/ }).length).toBeGreaterThan(0);
});

it('uses the official federal calendar when the provider has no state-specific election', async () => {
  // The availability field is intentionally absent to prove the Pages-first
  // frontend remains compatible with the currently deployed API contract.
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ items: [
    { id: '2000', name: 'VIP Test Election', election_day: '2031-12-06', division_id: 'ocd-division/country:us' },
    { id: '12', name: 'Delaware Primary Election', election_day: '2026-09-15', division_id: 'ocd-division/country:us/state:de' },
  ] }) });
  vi.stubGlobal('fetch', fetchMock);
  render(<MemoryRouter><ElectionsPage /></MemoryRouter>);
  expect(screen.queryByText('VIP Test Election')).toBeNull();
  fireEvent.change(screen.getByLabelText('State or District of Columbia'), { target: { value: 'MD' } });
  await screen.findByLabelText('1. ZIP code');
  fireEvent.click(screen.getByRole('button', { name: 'Continue with state information' }));
  expect(await screen.findByText('November 7, 2028 General Election')).toBeTruthy();
  expect(screen.getByRole('button', { name: 'Use my address' })).toBeTruthy();
  expect(screen.getAllByRole('link', { name: /Maryland voting rules/ })[0].getAttribute('href')).toBe('https://vote.gov/register/maryland');
  expect(screen.getAllByRole('link', { name: /Check registration and polling place/ })[0].getAttribute('href')).toBe('https://www.eac.gov/maryland-voter-info');
  expect(screen.getAllByRole('link', { name: /Ballot and local election office/ })[0].getAttribute('href')).toBe('https://www.eac.gov/voters/register-and-vote-in-your-state');
  expect(screen.getAllByText(/Live publisher page/).length).toBeGreaterThanOrEqual(3);
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

it('uses the official federal fallback when live calendar providers are unavailable', async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: false, status: 503, statusText: 'Service Unavailable',
    json: async () => ({ detail: 'Election provider is temporarily unavailable. Coverage could not be checked.' }),
  });
  vi.stubGlobal('fetch', fetchMock);
  render(<MemoryRouter><ElectionsPage /></MemoryRouter>);
  fireEvent.change(screen.getByLabelText('State or District of Columbia'), { target: { value: 'MD' } });
  expect(await screen.findByText('Using the most recent available election catalog.')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Continue with state information' }));
  expect(screen.getByText('November 7, 2028 General Election')).toBeTruthy();
  expect(screen.getByRole('button', { name: 'Use my address' })).toBeTruthy();
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

it('fills Missouri from its official calendar when live APIs are unavailable', async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: false, status: 503, statusText: 'Service Unavailable',
    json: async () => ({ detail: 'Election provider is temporarily unavailable.' }),
  });
  vi.stubGlobal('fetch', fetchMock);
  render(<MemoryRouter><ElectionsPage /></MemoryRouter>);
  fireEvent.change(screen.getByLabelText('State or District of Columbia'), { target: { value: 'MO' } });
  await screen.findByLabelText('1. ZIP code');
  fireEvent.click(screen.getByRole('button', { name: 'Continue with state information' }));
  expect(await screen.findByText('General Municipal Election Day')).toBeTruthy();
  expect(screen.getAllByText(/Missouri Secretary of State/).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/Provider-listed regular registration deadline:/)[0].textContent).toContain('January 6, 2027');
});

it('qualifies the Illinois primary and adds the consolidated election from the official calendar', async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({
    availability: catalogAvailability,
    source: { name: source.name, official_only: true },
    items: [{
      id: 'il-primary', name: 'Primary Election', election_day: '2027-02-23',
      division_id: 'ocd-division/country:us/state:il', description: null,
      registration_deadline: '2027-01-26', source,
    }],
  }) });
  vi.stubGlobal('fetch', fetchMock);
  render(<MemoryRouter><ElectionsPage /></MemoryRouter>);
  fireEvent.change(screen.getByLabelText('State or District of Columbia'), { target: { value: 'IL' } });
  await screen.findByLabelText('1. ZIP code');
  fireEvent.click(screen.getByRole('button', { name: 'Continue with state information' }));
  expect(await screen.findByText('February 23, 2027 Consolidated Primary — only where applicable')).toBeTruthy();
  expect(screen.getByText(/held only in jurisdictions that require one/)).toBeTruthy();
  expect(screen.getByText('April 6, 2027 Consolidated Election')).toBeTruthy();
  expect(screen.getByText(/Provider-listed regular registration deadline:/).textContent).toContain('January 26, 2027');
  expect(screen.getByText(/Deadlines vary by registration method/)).toBeTruthy();
  expect(screen.queryByRole('button', { name: 'Find my exact polling address' })).toBeNull();
  expect(screen.queryByRole('button', { name: 'Use private address lookup' })).toBeNull();
});

it('labels cached election coverage as stale while keeping supported lookup available', async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({
    availability: { ...catalogAvailability, status: 'stale' },
    source: { name: 'Google Civic Information API', official_only: true },
    items: [{ id: '12', name: 'Delaware Primary Election', election_day: '2026-09-15', division_id: 'ocd-division/country:us/state:de', description: null, registration_deadline: null, source }],
  }) });
  vi.stubGlobal('fetch', fetchMock);
  render(<MemoryRouter><ElectionsPage /></MemoryRouter>);
  fireEvent.change(screen.getByLabelText('State or District of Columbia'), { target: { value: 'DE' } });
  expect((await screen.findByRole('status')).textContent).toContain('Using the most recent available election catalog.');
  expect(screen.getByLabelText('1. ZIP code')).toBeTruthy();
  expect(fetchMock).toHaveBeenCalledTimes(1);
});
