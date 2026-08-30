import { afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import IssueDetailPage from '../pages/IssueDetailPage';

describe('IssueDetailPage journey actions', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('carries issue context into discussion, solutions, and representative lookup', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ slug: 'housing-rent', title: 'Housing & Rent', summary: 'Reviewed evidence.' }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ issue_slug: 'housing-rent', series: [] }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ issue_slug: 'housing-rent', total: 0, bills: [] }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ total: 1, videos: [{ video_id: 'housing-video', content_origin: 'community', caption: 'Housing explained', creator_label: 'Community member', issue: { slug: 'housing-rent', title: 'Housing & Rent' } }] }) }));

    render(
      <MemoryRouter initialEntries={['/issues/housing-rent']}>
        <Routes><Route path="/issues/:slug" element={<IssueDetailPage />} /></Routes>
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByRole('heading', { name: 'Housing & Rent' })).toBeTruthy());
    expect(screen.getByRole('link', { name: '0 evidence series' }).getAttribute('href')).toBe('/issues/housing-rent#evidence');
    expect(screen.getByRole('link', { name: '0 official bills' }).getAttribute('href')).toBe('/issues/housing-rent#legislation');
    expect(screen.getByRole('link', { name: 'Solutions' }).getAttribute('href')).toBe('/issues/housing-rent/solutions');
    expect(screen.getByRole('link', { name: 'Discuss' }).getAttribute('href')).toBe('/discuss?issue=housing-rent');
    expect(screen.getByRole('link', { name: 'Representatives' }).getAttribute('href')).toBe('/politics/find-rep?issue=housing-rent');
    expect(screen.getByRole('link', { name: 'Government' }).getAttribute('href')).toBe('/government?issue=housing-rent');
    expect(screen.getByRole('link', { name: 'Courts' }).getAttribute('href')).toBe('/courts?issue=housing-rent');
    expect(screen.getByRole('link', { name: /Housing explained/ }).getAttribute('href')).toBe('/watch/housing-video');
    expect(screen.getByText('Community shared')).toBeTruthy();
    expect(vi.mocked(fetch).mock.calls.some(([input]) => String(input).includes('/videos?limit=25&issue_slug=housing-rent'))).toBe(true);
    const issueNavigation = screen.getByRole('navigation', { name: 'Explore this issue' });
    expect(within(issueNavigation).getByRole('link', { name: /Sourced evidence/ }).getAttribute('href')).toBe('/issues/housing-rent#evidence');
    expect(within(issueNavigation).getByRole('link', { name: /Elections/ }).getAttribute('href')).toBe('/elections?issue=housing-rent');
    expect(screen.getByRole('link', { name: /Take action on this issue/ }).getAttribute('href')).toBe('/act?target_type=issue&target_id=housing-rent');
  });

  it('keeps the hub visible when a supporting section fails', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ slug: 'housing-rent', title: 'Housing & Rent', summary: 'Reviewed evidence.' }) })
      .mockRejectedValueOnce(new Error('network'))
      .mockResolvedValueOnce({ ok: true, json: async () => ({ issue_slug: 'housing-rent', total: 0, bills: [] }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ total: 0, videos: [] }) }));
    render(<MemoryRouter initialEntries={['/issues/housing-rent']}><Routes><Route path="/issues/:slug" element={<IssueDetailPage />} /></Routes></MemoryRouter>);
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Housing & Rent' })).toBeTruthy());
    expect(screen.getByText('Evidence is temporarily unavailable. Other issue connections remain accessible.')).toBeTruthy();
  });

  it('scrolls to legislation when its same-page hub link is selected', async () => {
    const scrollIntoView = vi.fn();
    Element.prototype.scrollIntoView = scrollIntoView;
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ slug: 'housing-rent', title: 'Housing & Rent', summary: 'Reviewed evidence.' }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ issue_slug: 'housing-rent', series: [] }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ issue_slug: 'housing-rent', total: 0, bills: [] }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ total: 0, videos: [] }) }));

    render(<MemoryRouter initialEntries={['/issues/housing-rent']}><Routes><Route path="/issues/:slug" element={<IssueDetailPage />} /></Routes></MemoryRouter>);
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Housing & Rent' })).toBeTruthy());
    const issueNavigation = screen.getByRole('navigation', { name: 'Explore this issue' });
    fireEvent.click(within(issueNavigation).getByRole('link', { name: /Legislation/ }));
    await waitFor(() => expect(scrollIntoView).toHaveBeenCalledWith({ block: 'start' }));
  });

  it('shows official USAJOBS listings only on the jobs topic', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ slug: 'jobs-unemployment', title: 'Jobs & Unemployment', summary: 'Labor-market opportunity.' }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ issue_slug: 'jobs-unemployment', total: 1, series: [] }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ issue_slug: 'jobs-unemployment', total: 12, bills: [] }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ total: 0, videos: [] }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ total: 100, jobs: [{ position_title: 'Program Analyst', organization_name: 'Department of Labor', department_name: 'Department of Labor', salary_min: '80000', salary_max: '110000', location: 'Washington, DC', grade: '13', schedule_type: 'Full-time', start_date: '2026-08-30', end_date: '2026-09-15', url: 'https://www.usajobs.gov/job/123' }], source: { url: 'https://www.usajobs.gov/', publisher: 'USAJOBS', retrieved_at: '2026-08-30T00:00:00Z' } }) }));

    render(<MemoryRouter initialEntries={['/issues/jobs-unemployment']}><Routes><Route path="/issues/:slug" element={<IssueDetailPage />} /></Routes></MemoryRouter>);
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Federal jobs now open' })).toBeTruthy());
    expect(screen.getByRole('heading', { name: 'Program Analyst' })).toBeTruthy();
    expect(screen.getByRole('link', { name: /View official listing/ }).getAttribute('href')).toBe('https://www.usajobs.gov/job/123');
    expect(screen.getByText(/100 current USAJOBS listings/)).toBeTruthy();
  });
});
