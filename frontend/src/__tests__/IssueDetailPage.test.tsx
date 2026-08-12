import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import IssueDetailPage from '../pages/IssueDetailPage';

describe('IssueDetailPage journey actions', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('carries issue context into discussion, solutions, and representative lookup', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ slug: 'housing-rent', title: 'Housing & Rent', summary: 'Reviewed evidence.' }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ issue_slug: 'housing-rent', series: [] }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ issue_slug: 'housing-rent', bills: [] }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ videos: [{ video_id: 'housing-video', caption: 'Housing explained', creator_label: 'Civic source', issue: { slug: 'housing-rent', title: 'Housing & Rent' } }] }) }));

    render(
      <MemoryRouter initialEntries={['/issues/housing-rent']}>
        <Routes><Route path="/issues/:slug" element={<IssueDetailPage />} /></Routes>
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByRole('heading', { name: 'Housing & Rent' })).toBeTruthy());
    expect(screen.getByRole('link', { name: '0 evidence series' }).getAttribute('href')).toBe('/issues/housing-rent#evidence');
    expect(screen.getByRole('link', { name: '0 reviewed bills' }).getAttribute('href')).toBe('/issues/housing-rent#legislation');
    expect(screen.getByRole('link', { name: 'Solutions' }).getAttribute('href')).toBe('/issues/housing-rent/solutions');
    expect(screen.getByRole('link', { name: 'Discuss' }).getAttribute('href')).toBe('/discuss?issue=housing-rent');
    expect(screen.getByRole('link', { name: 'Representatives' }).getAttribute('href')).toBe('/politics/find-rep?issue=housing-rent');
    expect(screen.getByRole('link', { name: 'Government' }).getAttribute('href')).toBe('/government?issue=housing-rent');
    expect(screen.getByRole('link', { name: 'Courts' }).getAttribute('href')).toBe('/courts?issue=housing-rent');
    expect(screen.getByRole('link', { name: /Housing explained/ }).getAttribute('href')).toBe('/watch/housing-video');
  });

  it('keeps the hub visible when a supporting section fails', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ slug: 'housing-rent', title: 'Housing & Rent', summary: 'Reviewed evidence.' }) })
      .mockRejectedValueOnce(new Error('network'))
      .mockResolvedValueOnce({ ok: true, json: async () => ({ issue_slug: 'housing-rent', bills: [] }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ videos: [] }) }));
    render(<MemoryRouter initialEntries={['/issues/housing-rent']}><Routes><Route path="/issues/:slug" element={<IssueDetailPage />} /></Routes></MemoryRouter>);
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Housing & Rent' })).toBeTruthy());
    expect(screen.getByText('Evidence is temporarily unavailable. Other issue connections remain accessible.')).toBeTruthy();
  });
});
