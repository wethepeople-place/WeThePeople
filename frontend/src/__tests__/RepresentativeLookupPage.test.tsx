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
});
