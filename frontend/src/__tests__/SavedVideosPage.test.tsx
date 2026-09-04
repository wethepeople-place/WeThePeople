import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import SavedVideosPage from '../pages/SavedVideosPage'

const auth = vi.hoisted(() => ({
  isAuthenticated: true,
  loading: false,
  authedFetch: vi.fn(),
}))

vi.mock('../contexts/AuthContext', () => ({ useAuth: () => auth }))

const savedVideo = {
  video_id: 'housing-rent-road-act-explained',
  creator_label: 'Money Instructor',
  caption: 'Senate Passes Housing Bill',
  saved: true,
  delivery: { poster_url: '/watch-thumbnails/housing-rent-road-act-explained.jpg', source_label: 'Money Instructor' },
  issue: { slug: 'housing-rent', title: 'Housing & Rent' },
  source: { url: 'https://www.youtube.com/watch?v=maODCSHgPww', publisher: 'Money Instructor' },
}

describe('SavedVideosPage', () => {
  beforeEach(() => {
    auth.isAuthenticated = true
    auth.loading = false
    auth.authedFetch.mockReset()
  })

  it('renders only the private saved collection with exact Watch links', async () => {
    auth.authedFetch.mockResolvedValue({ ok: true, json: async () => ({ total: 1, videos: [savedVideo], has_more: false }) })
    render(<MemoryRouter initialEntries={['/saved']}><Routes><Route path="/saved" element={<SavedVideosPage />} /></Routes></MemoryRouter>)

    await waitFor(() => expect(screen.getByRole('heading', { name: 'Senate Passes Housing Bill' })).toBeTruthy())
    expect(screen.getByRole('link', { name: /Senate Passes Housing Bill/ }).getAttribute('href')).toBe('/videos/housing-rent-road-act-explained')
    expect(screen.getByText(/Only you can see this collection\./)).toBeTruthy()
    expect(auth.authedFetch).toHaveBeenCalledWith(expect.stringMatching(/\/videos\/saved$/), { cache: 'no-store' })
  })

  it('removes a saved video without exposing a save count', async () => {
    auth.authedFetch
      .mockResolvedValueOnce({ ok: true, json: async () => ({ total: 1, videos: [savedVideo], has_more: false }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ saved: false }) })
    render(<MemoryRouter initialEntries={['/saved']}><Routes><Route path="/saved" element={<SavedVideosPage />} /></Routes></MemoryRouter>)

    const remove = await screen.findByRole('button', { name: /Remove Senate Passes Housing Bill/ })
    fireEvent.click(remove)
    await waitFor(() => expect(screen.getByRole('heading', { name: 'No saved videos yet' })).toBeTruthy())
    expect(screen.queryByText(/save count/i)).toBeNull()
    expect(auth.authedFetch).toHaveBeenLastCalledWith(expect.stringMatching(/\/videos\/housing-rent-road-act-explained\/save$/), expect.objectContaining({ method: 'PUT' }))
  })

  it('redirects signed-out visitors to login with a return path', () => {
    auth.isAuthenticated = false
    render(<MemoryRouter initialEntries={['/saved']}><Routes><Route path="/saved" element={<SavedVideosPage />} /><Route path="/login" element={<div>Login destination</div>} /></Routes></MemoryRouter>)
    expect(screen.getByText('Login destination')).toBeTruthy()
  })
})
