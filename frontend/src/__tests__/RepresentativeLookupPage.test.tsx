import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import RepresentativeLookupPage from '../pages/RepresentativeLookupPage';

vi.mock('../components/SectorHeader', () => ({ PoliticsSectorHeader: () => null }));
vi.mock('../contexts/AuthContext', () => ({ useAuth: () => ({ isAuthenticated: false }) }));

describe('RepresentativeLookupPage coverage state', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('does not call a valid ZIP invalid when tracked state data is absent', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ zip_code: '21136', state: 'MD', representatives: [] }),
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<MemoryRouter initialEntries={['/politics/find-rep?issue=housing-rent']}><RepresentativeLookupPage /></MemoryRouter>);
    fireEvent.change(screen.getByPlaceholderText(/Enter your zip code/), { target: { value: '21136' } });
    fireEvent.click(screen.getByRole('button', { name: /look up/i }));

    await waitFor(() => expect(screen.getByText('Representative data is not yet available here')).toBeTruthy());
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/lookup/21136'), { cache: 'no-store' });
    expect(screen.getByText(/resolves to MD/)).toBeTruthy();
    expect(screen.queryByText(/Please check the zip code/)).toBeNull();
    expect(screen.getByRole('link', { name: 'Official House lookup' }).getAttribute('href')).toBe('https://ziplook.house.gov/htbin/findrep_house?ZIP=21136');
    expect(screen.getByRole('link', { name: 'Official Senate lookup' }).getAttribute('href')).toBe('https://www.senate.gov/senators/senators-contact.htm?State=MD');
  });

  it('shows senators and requests an address when a ZIP crosses House districts', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        zip_code: '21208',
        state: 'MD',
        district_resolution_required: true,
        representatives: [
          {
            person_id: 'a000382', name: 'Angela D. Alsobrooks', party: 'D', chamber: 'senate', state: 'MD', district: null,
            votes: [{ question: 'On Passage', vote_date: '2026-10-10', result: 'Passed', position: 'Yea', related_bill: 'S123', source_url: 'https://www.congress.gov/vote/1', source_name: 'Congress.gov' }],
            bills: [{ bill_id: 's123-119', role: 'sponsor', title: 'A sourced test bill', policy_area: 'Housing', status: 'introduced', latest_action: 'Introduced', latest_action_date: '2026-10-01', source_url: 'https://www.congress.gov/bill/119th-congress/senate-bill/123', source_name: 'Congress.gov' }],
            election_forecasts: [{ id: 1, question: 'Who will win?', candidate_option: { key: 'angela', label: 'Angela D. Alsobrooks' }, closes_at: '2028-11-07', source_url: 'https://elections.maryland.gov', source_name: 'Official election source', forecast_url: '/forecasts' }],
          },
          { person_id: 'v000128', name: 'Chris Van Hollen', party: 'D', chamber: 'senate', state: 'MD', district: null },
        ],
      }),
    }));

    render(<MemoryRouter><RepresentativeLookupPage /></MemoryRouter>);
    fireEvent.change(screen.getByPlaceholderText(/Enter your zip code/), { target: { value: '21208' } });
    fireEvent.click(screen.getByRole('button', { name: /look up/i }));

    await waitFor(() => expect(screen.getAllByText('Angela D. Alsobrooks').length).toBeGreaterThan(0));
    expect(screen.getByRole('navigation', { name: 'Representative action steps' })).toBeTruthy();
    expect(screen.getByText('A representative')).toBeTruthy();
    expect(screen.getByText('Their public record')).toBeTruthy();
    expect(screen.getByText('Contact the office')).toBeTruthy();
    expect(screen.queryByRole('heading', { name: 'What do you think happens next?' })).toBeNull();
    expect(screen.getByRole('heading', { name: 'What do you think happens next for Angela D. Alsobrooks?' })).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'What do you think happens next for Chris Van Hollen?' })).toBeTruthy();
    expect(screen.getAllByRole('link', { name: 'View promises' })[0].getAttribute('href')).toBe('/civic/promises?person_id=a000382&person_name=Angela%20D.%20Alsobrooks');
    expect(screen.getAllByText('Chris Van Hollen').length).toBeGreaterThan(0);
    expect(screen.getByText('House address needed')).toBeTruthy();
    expect(screen.getByText('S123')).toBeTruthy();
    expect(screen.getByText('A sourced test bill')).toBeTruthy();
    expect(screen.getByText('Who will win?')).toBeTruthy();
    expect(screen.getByText(/No sourced forecast is published for Chris Van Hollen/)).toBeTruthy();
    expect(screen.getByRole('link', { name: /Enter your street address/ }).getAttribute('href')).toBe('https://ziplook.house.gov/htbin/findrep_house?ZIP=21208');
    expect(screen.queryByText('Representative data is not yet available here')).toBeNull();
  });
});
