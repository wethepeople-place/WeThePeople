import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import WatchVideoPage from '../pages/WatchVideoPage'

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ isAuthenticated: false, authedFetch: fetch }),
}))


describe('WatchVideoPage', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ total: 0, videos: [], next_cursor: null, has_more: false }),
    }))
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      value: vi.fn().mockReturnValue({ matches: false }),
    })
    vi.stubGlobal('IntersectionObserver', class {
      observe() {}
      unobserve() {}
      disconnect() {}
    })
    Object.defineProperty(Element.prototype, 'scrollIntoView', {
      configurable: true,
      value: vi.fn(),
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('settles an empty successful feed without creating video embeds', async () => {
    const { container } = render(
      <MemoryRouter initialEntries={['/watch']}>
        <Routes>
          <Route path="/watch" element={<WatchVideoPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('No civic videos are published yet.')).toBeTruthy()
    })
    expect(screen.queryByText('Loading Watch…')).toBeNull()
    expect(container.querySelectorAll('iframe')).toHaveLength(0)
    expect(container.querySelectorAll('video')).toHaveLength(0)
    expect(screen.getByRole('link', { name: 'Explore the Civic Hub' }).getAttribute('href')).toBe('/civic')
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
    expect(container.querySelector('img')?.getAttribute('src')).toBe('/watch-thumbnails/housing-rent-road-act-explained.jpg')
    expect(container.querySelectorAll('iframe')).toHaveLength(0)
  })
})
