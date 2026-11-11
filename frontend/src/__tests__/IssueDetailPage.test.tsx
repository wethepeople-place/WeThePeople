import { afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import IssueDetailPage from '../pages/IssueDetailPage';

vi.mock('../contexts/AuthContext', () => ({ useAuth: () => ({ isAuthenticated: false, authedFetch: fetch }) }));

const source = { url: 'https://example.gov/source', publisher: 'Official source', retrieved_at: '2026-11-01T00:00:00Z' };

function renderIssue(path = '/issues/immigration') {
  return render(<MemoryRouter initialEntries={[path]}><Routes><Route path="/issues/:slug" element={<IssueDetailPage />} /></Routes></MemoryRouter>);
}

function mockIssueFetch({ evidence = [], bills = [], videos = [], billTotal = bills.length, videoTotal = videos.length }: {
  evidence?: unknown[]; bills?: unknown[]; videos?: unknown[]; billTotal?: number; videoTotal?: number;
} = {}) {
  vi.stubGlobal('fetch', vi.fn().mockImplementation((input: string) => {
    const url = String(input);
    const payload = url.includes('/discussions/videos/') ? { items: [] }
      : url.includes('/evidence') ? { issue_slug: 'immigration', series: evidence }
      : url.includes('/bills') ? { issue_slug: 'immigration', total: billTotal, bills }
        : url.includes('/videos') ? { total: videoTotal, videos }
          : { slug: 'immigration', title: 'Immigration', summary: 'Immigration, border policy, DACA, family separation, and ICE.' };
    return Promise.resolve({ ok: true, json: async () => payload });
  }));
}

describe('IssueDetailPage guided issue journey', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('presents a simple four-step Immigration flow and distinct action destinations', async () => {
    mockIssueFetch();
    renderIssue();

    await waitFor(() => expect(screen.getByRole('heading', { name: 'Immigration' })).toBeTruthy());
    expect(screen.getByText('Step 1 · Understand the data')).toBeTruthy();
    expect(screen.getByText('Step 2 · Learn and discuss')).toBeTruthy();
    expect(screen.getByText('Step 3 · Follow the decisions')).toBeTruthy();
    expect(screen.getByText('Step 4 · Choose an action')).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Watch and discuss immigration' })).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Immigration legislation' })).toBeTruthy();
    expect(screen.queryByText('Join this community')).toBeNull();
    expect(screen.queryByText('Discussions')).toBeNull();
    expect(screen.queryByText('Proposals')).toBeNull();
    expect(screen.queryByText(/Layout demo/)).toBeNull();

    expect(screen.getByRole('link', { name: /Contact your representatives/ }).getAttribute('href')).toBe('/politics/find-rep?issue=immigration');
    expect(screen.getByRole('link', { name: /Review the legislation/ }).getAttribute('href')).toBe('/issues/immigration#legislation');
    expect(screen.getByRole('link', { name: /Prepare to vote/ }).getAttribute('href')).toBe('/act?target_type=issue&target_id=immigration#act-option-vote');
    expect(vi.mocked(fetch).mock.calls.some(([input]) => String(input).includes('/discussions'))).toBe(false);
  });

  it('shows a comparable Census immigration series with exact annual values', async () => {
    mockIssueFetch({ evidence: [{
      key: 'agenda-immigration', title: 'Adults naming Immigration as a 2026 government priority',
      unit: 'percent of U.S. adults', geography: { type: 'country', id: 'US' }, source,
      observations: [{ date: '2025-12-08', value: 44, source_record_id: 'agenda-2026', source }],
    }] });
    renderIssue();

    await waitFor(() => expect(screen.getByRole('heading', { name: 'Immigration facts & trends' })).toBeTruthy());
    expect(screen.getByRole('heading', { name: 'Net international migration to the United States' })).toBeTruthy();
    expect(screen.getByText('376,026')).toBeTruthy();
    expect(screen.getByText('2,734,468')).toBeTruthy();
    expect(screen.getByText('1,262,202')).toBeTruthy();
    expect(screen.getByText('54% lower than 2024')).toBeTruthy();
    expect(screen.queryByText('44%')).toBeNull();
    expect(screen.getByRole('link', { name: /U.S. Census Bureau/ })).toBeTruthy();
  });

  it('shows one video section, guides discussion through videos, and expands real items only', async () => {
    const videos = Array.from({ length: 4 }, (_, index) => ({
      video_id: `video-${index + 1}`, content_origin: index === 0 ? 'community' : 'reviewed',
      caption: `Immigration video ${index + 1}`, creator_label: 'Public broadcaster',
      delivery: { provider: 'youtube', provider_video_id: `youtube-${index + 1}`, poster_url: `/videos/${index + 1}.jpg` },
      issue: { slug: 'immigration', title: 'Immigration' },
    }));
    mockIssueFetch({ videos, videoTotal: 39 });
    renderIssue();

    const watch = await screen.findByRole('region', { name: 'Watch and discuss immigration' });
    expect(within(watch).getAllByRole('button', { name: /Watch and discuss:/ })).toHaveLength(3);
    expect(within(watch).getByText('Shared by a community member')).toBeTruthy();
    expect(within(watch).getAllByText('Reviewed source')).toHaveLength(2);
    fireEvent.click(within(watch).getByRole('button', { name: 'Show 1 more videos' }));
    expect(within(watch).getAllByRole('button', { name: /Watch and discuss:/ })).toHaveLength(4);
    expect(within(watch).getByText('Showing 4 recent videos from 39 connected to immigration.')).toBeTruthy();
  });

  it('opens a video with engagement and comments without leaving the issue page', async () => {
    mockIssueFetch({ videos: [{
      video_id: 'immigration-video', content_origin: 'reviewed', caption: 'Immigration explained', creator_label: 'Public broadcaster',
      delivery: { mode: 'official_embed', provider: 'youtube', provider_video_id: 'abc123', canonical_url: 'https://www.youtube.com/watch?v=abc123', source_label: 'YouTube', poster_url: null, development_only: false },
      issue: { slug: 'immigration', title: 'Immigration' }, like_count: 4, discussion_count: 2,
    }] });
    renderIssue();

    fireEvent.click(await screen.findByRole('button', { name: 'Watch and discuss: Immigration explained' }));
    const dialog = await screen.findByRole('dialog', { name: 'Immigration explained' });
    expect(within(dialog).getByText('Watch without leaving this issue')).toBeTruthy();
    expect(within(dialog).getByLabelText('Comments for Immigration explained')).toBeTruthy();
    expect(within(dialog).getByRole('link', { name: 'Open full video page' }).getAttribute('href')).toBe('/videos/immigration-video');
    fireEvent.click(within(dialog).getByRole('button', { name: 'Close video' }));
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Immigration explained' })).toBeNull());
    expect(screen.getByRole('heading', { name: 'Immigration' })).toBeTruthy();
  });

  it('uses readable bill cards with relevance, latest action, and a predictable expansion', async () => {
    const bills = Array.from({ length: 5 }, (_, index) => ({
      bill_id: `hr${index + 1}-119`, congress: 119, bill_type: 'hr', bill_number: index + 1,
      title: `Immigration bill ${index + 1}`, phase: 'current', relevance_note: 'Connected through the official Immigration policy area.',
      latest_action_text: 'Referred to the House Committee on the Judiciary.', latest_action_date: '2026-10-15', source,
    }));
    mockIssueFetch({ bills, billTotal: 689 });
    renderIssue();

    await waitFor(() => expect(screen.getAllByRole('link', { name: /View bill/ })).toHaveLength(3));
    expect(screen.getAllByText('What this bill would do')).toHaveLength(3);
    expect(screen.getAllByText(/A trustworthy plain-language summary/)).toHaveLength(3);
    expect(screen.getAllByText('Status and official details')).toHaveLength(3);
    expect(screen.getByText('Showing 5 recent bills from 689 connected through the official Congress.gov policy area. Relevance is not an endorsement.')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Show 2 more bills' }));
    expect(screen.getAllByRole('link', { name: /View bill/ })).toHaveLength(5);
  });

  it('keeps the journey useful when supporting data is unavailable', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ slug: 'immigration', title: 'Immigration', summary: 'Immigration policy.' }) })
      .mockRejectedValueOnce(new Error('network'))
      .mockRejectedValueOnce(new Error('network'))
      .mockRejectedValueOnce(new Error('network')));
    renderIssue();

    await waitFor(() => expect(screen.getByText('Sourced data is temporarily unavailable. You can still watch videos, review legislation, and act below.')).toBeTruthy());
    expect(screen.getByText('Videos are temporarily unavailable. You can still review legislation and take action below.')).toBeTruthy();
    expect(screen.getByText('Legislation is temporarily unavailable. You can still contact representatives or prepare to vote below.')).toBeTruthy();
    expect(screen.getByRole('link', { name: /Contact your representatives/ })).toBeTruthy();
  });

  it('shows official USAJOBS listings only on the jobs topic', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ slug: 'jobs-unemployment', title: 'Jobs & Unemployment', summary: 'Labor-market opportunity.' }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ issue_slug: 'jobs-unemployment', series: [] }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ issue_slug: 'jobs-unemployment', total: 0, bills: [] }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ total: 0, videos: [] }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ total: 100, jobs: [{ position_title: 'Program Analyst', organization_name: 'Department of Labor', department_name: 'Department of Labor', location: 'Washington, DC', schedule_type: 'Full-time', url: 'https://www.usajobs.gov/job/123' }], source }) }));
    renderIssue('/issues/jobs-unemployment');

    await waitFor(() => expect(screen.getByRole('heading', { name: 'Federal jobs now open' })).toBeTruthy());
    expect(screen.getByRole('heading', { name: 'Program Analyst' })).toBeTruthy();
    expect(screen.getByRole('link', { name: /View official listing/ }).getAttribute('href')).toBe('https://www.usajobs.gov/job/123');
  });
});
