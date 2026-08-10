import { afterEach, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import CourtsPage from '../pages/CourtsPage';

afterEach(() => vi.unstubAllGlobals());

it('renders an honest empty issue-scoped Courts state', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ total: 0, limit: 20, offset: 0, items: [] }) }));
  render(<MemoryRouter initialEntries={['/courts?issue=housing-rent']}><CourtsPage /></MemoryRouter>);
  await waitFor(() => expect(screen.getByText('No reviewed court proceedings yet')).toBeTruthy());
  expect(screen.getByText(/Allegations are not findings, and filings are not decisions\./)).toBeTruthy();
  expect(screen.getByRole('link', { name: 'Return to official issue evidence' }).getAttribute('href')).toBe('/issues/housing-rent');
});

it('filters by bill and preserves the return path', async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ total: 0, limit: 20, offset: 0, items: [] }) });
  vi.stubGlobal('fetch', fetchMock);
  render(<MemoryRouter initialEntries={['/courts?bill=hr1-119']}><CourtsPage /></MemoryRouter>);
  await waitFor(() => expect(screen.getByText('No reviewed court proceedings yet')).toBeTruthy());
  expect(fetchMock.mock.calls[0][0]).toContain('bill_id=hr1-119');
  expect(screen.getByRole('link', { name: 'Return to bill details' }).getAttribute('href')).toBe('/politics/bill/hr1-119');
});
