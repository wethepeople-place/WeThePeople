import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ActHubPage from '../pages/ActHubPage'

vi.mock('../contexts/AuthContext', () => ({ useAuth: () => ({ isAuthenticated: false }) }))

describe('ActHubPage', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation((input: string) => Promise.resolve({
      ok: true,
      json: async () => input.includes('/act/circles') ? { items: [] } : { items: [] },
    })))
  })

  it('offers four clear action destinations and keeps legal enrollment disabled', async () => {
    render(<MemoryRouter><ActHubPage /></MemoryRouter>)
    expect(screen.getByRole('heading', { name: 'ACT' })).toBeTruthy()
    expect(screen.getByRole('link', { name: /Elections/ }).getAttribute('href')).toBe('/elections')
    expect(screen.getByRole('link', { name: /Representatives/ }).getAttribute('href')).toBe('/politics/find-rep')
    expect(screen.getByRole('link', { name: /Activities/ }).getAttribute('href')).toBe('#activities')
    expect(screen.getByRole('link', { name: /Action Circles/ }).getAttribute('href')).toBe('#circles')
    expect(await screen.findByText('No moderated Circles are public yet')).toBeTruthy()
    expect(screen.getByText('About future legal pathways')).toBeTruthy()
    expect(screen.getByText(/Legal pathways are not enabled/)).toBeTruthy()
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2))
  })
})
