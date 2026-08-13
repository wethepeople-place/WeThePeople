import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import RepresentativeLookupPage from '../pages/RepresentativeLookupPage';

vi.mock('../components/SectorHeader', () => ({ PoliticsSectorHeader: () => null }));

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
          { person_id: 'a000382', name: 'Angela D. Alsobrooks', party: 'D', chamber: 'senate', state: 'MD', district: null },
          { person_id: 'v000128', name: 'Chris Van Hollen', party: 'D', chamber: 'senate', state: 'MD', district: null },
        ],
      }),
    }));

    render(<MemoryRouter><RepresentativeLookupPage /></MemoryRouter>);
    fireEvent.change(screen.getByPlaceholderText(/Enter your zip code/), { target: { value: '21208' } });
    fireEvent.click(screen.getByRole('button', { name: /look up/i }));

    await waitFor(() => expect(screen.getByText('Angela D. Alsobrooks')).toBeTruthy());
    expect(screen.getByText('Chris Van Hollen')).toBeTruthy();
    expect(screen.getByText('House address needed')).toBeTruthy();
    expect(screen.getByRole('link', { name: /Enter your street address/ }).getAttribute('href')).toBe('https://ziplook.house.gov/htbin/findrep_house?ZIP=21208');
    expect(screen.queryByText('Representative data is not yet available here')).toBeNull();
  });
});
