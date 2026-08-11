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
})
