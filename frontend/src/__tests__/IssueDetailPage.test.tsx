import { afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import IssueDetailPage from '../pages/IssueDetailPage';

describe('IssueDetailPage journey actions', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('carries issue context into one Community destination and representative lookup', async () => {
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
    expect(screen.getAllByRole('link', { name: /Community/ }).some((link) => link.getAttribute('href') === '/discuss?issue=housing-rent')).toBe(true);
    expect(screen.queryByRole('link', { name: 'Solutions' })).toBeNull();
    expect(screen.queryByRole('link', { name: 'Discuss' })).toBeNull();
    expect(screen.getByRole('link', { name: 'Representatives' }).getAttribute('href')).toBe('/politics/find-rep?issue=housing-rent');
    expect(screen.getByRole('link', { name: 'Government' }).getAttribute('href')).toBe('/government?issue=housing-rent');
    expect(screen.getByRole('link', { name: 'Courts' }).getAttribute('href')).toBe('/courts?issue=housing-rent');
    expect(screen.getAllByRole('link', { name: /Housing explained/ })[0].getAttribute('href')).toBe('/watch/housing-video?play=1');
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

  it('shows at most three real related records in each hub preview', async () => {
    const videos = Array.from({ length: 4 }, (_, index) => ({ video_id: `video-${index + 1}`, content_origin: 'community', caption: `Video ${index + 1}`, creator_label: 'Community member', delivery: { provider: 'youtube', provider_video_id: `youtube-${index + 1}`, poster_url: `/videos/community/${index + 1}/poster` }, issue: { slug: 'housing-rent', title: 'Housing & Rent' } }));
    const bills = Array.from({ length: 4 }, (_, index) => ({ bill_id: `hr-${index + 1}-119`, bill_type: 'hr', bill_number: String(index + 1), congress: 119, title: `Bill ${index + 1}`, phase: 'current', source: { url: 'https://congress.gov', publisher: 'Congress.gov', retrieved_at: '2026-08-30T00:00:00Z' } }));
    const discussions = Array.from({ length: 4 }, (_, index) => ({ id: index + 1, body: `Discussion ${index + 1}`, author: { display_name: 'Neighbor' }, reply_count: index }));
    vi.stubGlobal('fetch', vi.fn().mockImplementation((input: string) => {
      const url = String(input);
      const payload = url.includes('/evidence') ? { issue_slug: 'housing-rent', series: [] }
        : url.includes('/bills') ? { issue_slug: 'housing-rent', total: 4, bills }
          : url.includes('/videos') ? { total: 4, videos }
            : url.includes('/discussions?') ? { total: 4, limit: 5, offset: 0, items: discussions }
                : { slug: 'housing-rent', title: 'Housing & Rent', summary: 'Reviewed evidence.' };
      return Promise.resolve({ ok: true, json: async () => payload });
    }));

    render(<MemoryRouter initialEntries={['/issues/housing-rent']}><Routes><Route path="/issues/:slug" element={<IssueDetailPage />} /></Routes></MemoryRouter>);
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Housing & Rent' })).toBeTruthy());
    expect(within(screen.getByLabelText('Videos preview')).getAllByRole('link')).toHaveLength(3);
    expect(screen.getByLabelText('Videos preview').querySelectorAll('img')).toHaveLength(3);
    const civicVideos = screen.getByRole('region', { name: 'Civic videos' });
    expect(within(civicVideos).getAllByRole('link')).toHaveLength(3);
    expect(civicVideos.querySelectorAll('img')).toHaveLength(3);
    fireEvent.click(within(civicVideos).getByRole('button', { name: 'View 1 more videos' }));
    expect(within(civicVideos).getAllByRole('link')).toHaveLength(4);
    fireEvent.click(within(civicVideos).getByRole('button', { name: 'Show fewer videos' }));
    expect(within(civicVideos).getAllByRole('link')).toHaveLength(3);
    expect(within(screen.getByLabelText('Legislation preview')).getAllByRole('link')).toHaveLength(3);
    await waitFor(() => expect(within(screen.getByLabelText('Community preview')).getAllByRole('link')).toHaveLength(3));
    expect(vi.mocked(fetch).mock.calls.some(([input]) => String(input).includes('/discussions?') && String(input).includes('limit=5'))).toBe(true);
    expect(vi.mocked(fetch).mock.calls.some(([input]) => String(input).includes('/solutions?'))).toBe(false);
  });

  it('shows three legislation cards before expanding the related bills', async () => {
    const bills = Array.from({ length: 5 }, (_, index) => ({ bill_id: `hr-${index + 1}-119`, bill_type: 'hr', bill_number: String(index + 1), congress: 119, title: `Legislation card ${index + 1}`, phase: 'current', source: { url: 'https://congress.gov', publisher: 'Congress.gov', retrieved_at: '2026-08-30T00:00:00Z' } }));
    vi.stubGlobal('fetch', vi.fn().mockImplementation((input: string) => {
      const url = String(input);
      const payload = url.includes('/evidence') ? { issue_slug: 'housing-rent', series: [] }
        : url.includes('/bills') ? { issue_slug: 'housing-rent', total: 5, bills }
          : url.includes('/videos') ? { total: 0, videos: [] }
            : url.includes('/discussions?') ? { total: 0, limit: 5, offset: 0, items: [] }
              : { slug: 'housing-rent', title: 'Housing & Rent', summary: 'Reviewed evidence.' };
      return Promise.resolve({ ok: true, json: async () => payload });
    }));

    render(<MemoryRouter initialEntries={['/issues/housing-rent']}><Routes><Route path="/issues/:slug" element={<IssueDetailPage />} /></Routes></MemoryRouter>);
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Housing & Rent' })).toBeTruthy());
    expect(screen.getAllByRole('link', { name: /Bill details/ })).toHaveLength(3);
    const seeMore = screen.getByRole('button', { name: 'See 2 more related bills' });
    expect(seeMore.getAttribute('aria-expanded')).toBe('false');
    fireEvent.click(seeMore);
    expect(screen.getAllByRole('link', { name: /Bill details/ })).toHaveLength(5);
    fireEvent.click(screen.getByRole('button', { name: 'Show fewer bills' }));
    expect(screen.getAllByRole('link', { name: /Bill details/ })).toHaveLength(3);
  });

  it('stacks previews vertically and clearly fills empty layouts with five demo cards', async () => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation((input: string) => {
      const url = String(input);
      const payload = url.includes('/evidence') ? { issue_slug: 'housing-rent', series: [] }
        : url.includes('/bills') ? { issue_slug: 'housing-rent', total: 0, bills: [] }
          : url.includes('/videos') ? { total: 0, videos: [] }
            : url.includes('/discussions?') ? { total: 0, limit: 5, offset: 0, items: [] }
              : { slug: 'housing-rent', title: 'Housing & Rent', summary: 'Reviewed evidence.' };
      return Promise.resolve({ ok: true, json: async () => payload });
    }));

    render(<MemoryRouter initialEntries={['/issues/housing-rent']}><Routes><Route path="/issues/:slug" element={<IssueDetailPage />} /></Routes></MemoryRouter>);
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Housing & Rent' })).toBeTruthy());
    const communityPreview = screen.getByLabelText('Community preview');
    expect(within(communityPreview).getAllByText('Layout demo · Not civic activity')).toHaveLength(3);
    fireEvent.click(within(communityPreview).getByRole('button', { name: 'See 2 more' }));
    expect(within(communityPreview).getAllByText('Layout demo · Not civic activity')).toHaveLength(5);
    expect(within(communityPreview).getByRole('button', { name: 'Show fewer' }).getAttribute('aria-expanded')).toBe('true');
  });
});
