import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import WatchVideoPage from '../pages/WatchVideoPage'

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ isAuthenticated: false, authedFetch: fetch }),
}))


describe('WatchVideoPage', () => {
  let observerCallback: IntersectionObserverCallback | undefined
  const scrollIntoView = vi.fn()

  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ total: 0, videos: [], next_cursor: null, has_more: false }),
    }))
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      value: vi.fn().mockReturnValue({ matches: false }),
    })
    observerCallback = undefined
    scrollIntoView.mockReset()
    vi.stubGlobal('IntersectionObserver', class {
      constructor(callback: IntersectionObserverCallback) { observerCallback = callback }
      observe() {}
      unobserve() {}
      disconnect() {}
    })
    Object.defineProperty(Element.prototype, 'scrollIntoView', {
      configurable: true,
      value: scrollIntoView,
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('continues an empty video feed with real Agenda material without creating embeds', async () => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation((input: string) => Promise.resolve({
      ok: true,
      json: async () => input.includes('/issues')
        ? { items: [{ slug: 'housing-rent', title: 'Housing & Rent', summary: 'A reviewed issue summary.', evidence_note: 'Rent evidence.', bill_count: 7 }] }
        : { total: 0, videos: [], next_cursor: null, has_more: false },
    })))
    const { container } = render(
      <MemoryRouter initialEntries={['/watch']}>
        <Routes>
          <Route path="/watch" element={<WatchVideoPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('Civic context · Agenda issue')).toBeTruthy()
    })
    expect(screen.queryByText('Loading Watch…')).toBeNull()
    expect(container.querySelectorAll('iframe')).toHaveLength(0)
    expect(container.querySelectorAll('video')).toHaveLength(0)
    expect(screen.getByRole('link', { name: 'Explore this issue' }).getAttribute('href')).toBe('/issues/housing-rent')
    expect(screen.getByRole('link', { name: /Share a civic video, link, or thought/ }).getAttribute('href')).toBe('/discuss?compose=1#composer')
    expect(screen.getByRole('link', { name: 'Post link' }).getAttribute('href')).toBe('/discuss?compose=1#composer')
    expect(screen.getByRole('button', { name: /Image — coming soon/ }).hasAttribute('disabled')).toBe(true)
    expect(screen.getByRole('button', { name: /Upload video — coming soon/ }).hasAttribute('disabled')).toBe(true)
  })

  it('shows a local reviewed thumbnail without loading the provider player', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        total: 1,
        next_cursor: null,
        has_more: false,
        videos: [{
          video_id: 'housing-rent-road-act-explained',
          creator_label: 'Money Instructor',
          caption: 'Senate Passes Housing Bill',
          transcript: 'Reviewed overview.',
          media_url: 'https://www.youtube.com/watch?v=maODCSHgPww',
          published_at: '2026-08-11T00:00:00Z',
          delivery: {
            mode: 'official_embed', provider: 'youtube', provider_video_id: 'maODCSHgPww',
            canonical_url: 'https://www.youtube.com/watch?v=maODCSHgPww', source_label: 'Money Instructor',
            poster_url: '/watch-thumbnails/housing-rent-road-act-explained.jpg', development_only: false,
          },
          accessibility: null,
          source: { url: 'https://www.youtube.com/watch?v=maODCSHgPww', publisher: 'Money Instructor' },
          issue: { slug: 'housing-rent', title: 'Housing & Rent' },
          bills: [], discussion_post_id: null, like_count: 0, discussion_count: 0, liked: false, saved: false,
        }],
      }),
    }))

    const { container } = render(
      <MemoryRouter initialEntries={['/watch/housing-rent-road-act-explained']}>
        <Routes><Route path="/watch/:videoId" element={<WatchVideoPage />} /></Routes>
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getByRole('button', { name: 'Play video from YouTube' })).toBeTruthy())
    expect(screen.getByRole('link', { name: 'Apply for a job' }).getAttribute('href')).toBe('/issues/jobs-unemployment#federal-jobs')
    expect(screen.getByRole('link', { name: 'Place your forecast' }).getAttribute('href')).toBe('/forecasts')
    expect(container.querySelector('img')?.getAttribute('src')).toBe('/watch-thumbnails/housing-rent-road-act-explained.jpg')
    expect(container.querySelector('img')?.parentElement?.className).toContain('absolute inset-0')
    expect(container.querySelectorAll('iframe')).toHaveLength(0)
    fireEvent.click(screen.getByRole('button', { name: 'Play video from YouTube' }))
    await waitFor(() => expect(container.querySelectorAll('iframe')).toHaveLength(1))
    expect(container.querySelector('iframe')?.getAttribute('src')).toContain('youtube-nocookie.com/embed/maODCSHgPww')
  })

  it('shows an automatically-fed community video with its proxied thumbnail', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        total: 1, next_cursor: null, has_more: false,
        videos: [{
          video_id: 'community-42', content_origin: 'community', creator_label: 'Community member',
          caption: 'YouTube video about Housing & Rent', transcript: null,
          media_url: 'https://www.youtube.com/shorts/ssTeslcxXbY', published_at: '2026-08-29T00:00:00Z',
          delivery: { mode: 'official_embed', provider: 'youtube', provider_video_id: 'ssTeslcxXbY', canonical_url: 'https://www.youtube.com/shorts/ssTeslcxXbY', source_label: 'YouTube', poster_url: '/videos/community/42/poster', development_only: false },
          accessibility: null, source: { url: 'https://www.youtube.com/shorts/ssTeslcxXbY', publisher: 'YouTube' },
          issue: { slug: 'housing-rent', title: 'Housing & Rent' }, bills: [], discussion_post_id: 42,
          like_count: 0, discussion_count: 1, liked: false, saved: false,
        }],
      }),
    }))

    const { container } = render(
      <MemoryRouter initialEntries={['/watch/community-42']}>
        <Routes><Route path="/watch/:videoId" element={<WatchVideoPage />} /></Routes>
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getByText('Community shared')).toBeTruthy())
    expect(screen.getByRole('link', { name: /Share a civic video, link, or thought/ }).getAttribute('href')).toBe('/discuss?compose=1#composer')
    expect(container.querySelector('img')?.getAttribute('src')).toBe('/api/videos/community/42/poster')
    expect(screen.queryByText('Reviewed source')).toBeNull()
    expect(screen.getByRole('link', { name: /Open this community conversation/ }).getAttribute('href')).toBe('/discuss/42')
    expect(screen.getByRole('button', { name: /Like video/ })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Save video privately' })).toBeTruthy()
    expect(screen.queryByRole('link', { name: /^YouTube/ })).toBeNull()
    expect(container.querySelectorAll('iframe')).toHaveLength(0)
  })

  it('opens the shared video conversation without leaving Watch', async () => {
    const video = {
      video_id: 'housing-rent-road-act-explained', creator_label: 'Money Instructor',
      caption: 'Senate Passes Housing Bill', transcript: 'Reviewed overview.',
      media_url: 'https://www.youtube.com/watch?v=maODCSHgPww', published_at: '2026-08-11T00:00:00Z',
      delivery: { mode: 'link_out', provider: 'youtube', provider_video_id: 'maODCSHgPww', canonical_url: 'https://www.youtube.com/watch?v=maODCSHgPww', source_label: 'Money Instructor', development_only: false },
      accessibility: null, source: { url: 'https://www.youtube.com/watch?v=maODCSHgPww', publisher: 'Money Instructor' },
      issue: { slug: 'housing-rent', title: 'Housing & Rent' }, bills: [], discussion_post_id: null,
      like_count: 0, discussion_count: 1, liked: false, saved: false,
    }
    vi.stubGlobal('fetch', vi.fn().mockImplementation((input: string) => Promise.resolve({
      ok: true,
      json: async () => input.includes('/discussions/videos/')
        ? { total: 1, limit: 20, offset: 0, items: [{ id: 9, body: 'Evidence first.', author: { id: null, display_name: 'Resident' }, reply_count: 0, attachments: [], created_at: '2026-08-11T00:00:00Z', moderation_status: 'published' }] }
        : { total: 1, videos: [video], next_cursor: null, has_more: false },
    })))

    const { container } = render(
      <MemoryRouter initialEntries={['/watch/housing-rent-road-act-explained']}>
        <Routes><Route path="/watch/:videoId" element={<WatchVideoPage />} /></Routes>
      </MemoryRouter>,
    )

    const trigger = await screen.findByRole('button', { name: /Open comments for this video/ })
    fireEvent.click(trigger)
    expect(await screen.findByRole('dialog', { name: /Comments for Senate Passes Housing Bill/ })).toBeTruthy()
    expect(screen.getByText('Evidence first.')).toBeTruthy()
    expect(screen.getByRole('link', { name: "View this video's full conversation" }).getAttribute('href')).toBe('/discuss?video=housing-rent-road-act-explained')
    expect(screen.getByRole('link', { name: 'Open full discussion' }).getAttribute('href')).toBe('/discuss/9')
    expect(screen.getByRole('link', { name: 'Sign in to comment' }).getAttribute('href')).toContain('comments%3D1')
    expect(container.querySelectorAll('iframe')).toHaveLength(0)
  })

  it('pages videos near the end and deduplicates canonical video IDs', async () => {
    const makeVideo = (video_id: string) => ({
      video_id, creator_label: 'Reviewed source', caption: `Video ${video_id}`,
      transcript: 'Reviewed overview.', media_url: `https://example.com/${video_id}`, published_at: '2026-08-11T00:00:00Z',
      delivery: { mode: 'link_out', provider: null, provider_video_id: null, canonical_url: `https://example.com/${video_id}`, source_label: 'Official source', development_only: false },
      accessibility: null, source: { url: `https://example.com/${video_id}`, publisher: 'Official source' },
      issue: { slug: 'housing-rent', title: 'Housing & Rent' }, bills: [], discussion_post_id: null,
      like_count: 0, discussion_count: 0, liked: false, saved: false,
    })
    vi.stubGlobal('fetch', vi.fn().mockImplementation((input: string) => Promise.resolve({
      ok: true,
      json: async () => input.includes('cursor=next-page')
        ? { total: 2, videos: [makeVideo('one'), makeVideo('two')], next_cursor: null, has_more: false }
        : { total: 2, videos: [makeVideo('one')], next_cursor: 'next-page', has_more: true },
    })))

    const { container } = render(
      <MemoryRouter initialEntries={['/watch/one']}>
        <Routes><Route path="/watch/:videoId" element={<WatchVideoPage />} /></Routes>
      </MemoryRouter>,
    )
    const feed = await screen.findByRole('main', { name: 'Civic video feed' })
    Object.defineProperties(feed, {
      scrollHeight: { configurable: true, value: 2000 },
      scrollTop: { configurable: true, value: 1200 },
      clientHeight: { configurable: true, value: 800 },
    })
    fireEvent.scroll(feed)
    await waitFor(() => expect(container.querySelectorAll('[data-video-id]')).toHaveLength(2))
    expect(container.querySelectorAll('[data-video-id="one"]')).toHaveLength(1)
    expect(vi.mocked(fetch).mock.calls.some(([input]) => String(input).includes('cursor=next-page'))).toBe(true)
  })

  it('does not force-scroll again when visibility updates the video URL', async () => {
    const videos = ['one', 'two'].map((video_id) => ({
      video_id, creator_label: 'Reviewed source', caption: `Video ${video_id}`,
      transcript: 'Reviewed overview.', media_url: `https://example.com/${video_id}`, published_at: '2026-08-11T00:00:00Z',
      delivery: { mode: 'link_out', provider: null, provider_video_id: null, canonical_url: `https://example.com/${video_id}`, source_label: 'Official source', development_only: false },
      accessibility: null, source: { url: `https://example.com/${video_id}`, publisher: 'Official source' },
      issue: { slug: 'housing-rent', title: 'Housing & Rent' }, bills: [], discussion_post_id: null,
      like_count: 0, discussion_count: 0, liked: false, saved: false,
    }))
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ total: 2, videos, next_cursor: null, has_more: false }) }))

    const { container } = render(
      <MemoryRouter initialEntries={['/watch/one']}>
        <Routes><Route path="/watch/:videoId" element={<WatchVideoPage />} /></Routes>
      </MemoryRouter>,
    )

    await waitFor(() => expect(container.querySelectorAll('[data-video-id]')).toHaveLength(2))
    expect(scrollIntoView).toHaveBeenCalledTimes(1)
    const second = container.querySelector<HTMLElement>('[data-video-id="two"]')!
    await act(async () => {
      observerCallback?.([{ isIntersecting: true, intersectionRatio: 1, target: second } as unknown as IntersectionObserverEntry], {} as IntersectionObserver)
    })
    expect(scrollIntoView).toHaveBeenCalledTimes(1)
    expect(vi.mocked(fetch).mock.calls.filter(([input]) => String(input).includes('/videos?')).length).toBe(1)
  })
})
