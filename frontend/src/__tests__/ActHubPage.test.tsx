import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import ActHubPage from '../pages/ActHubPage'

describe('ActHubPage', () => {
  it('offers supported action destinations and keeps unfinished community features hidden', () => {
    render(<MemoryRouter><ActHubPage /></MemoryRouter>)
    expect(screen.getByRole('heading', { name: 'ACT' })).toBeTruthy()
    expect(screen.getByTitle('Step 1: Plan my vote').getAttribute('src')).toBe('/elections?embed=1')
    expect(screen.getByTitle('Step 2: Contact my representatives').getAttribute('src')).toBe('/politics/find-rep?embed=1')
    expect(screen.queryByText('Action Circles')).toBeNull()
    expect(screen.queryByText('Activities')).toBeNull()
    expect(screen.queryByText('About future legal pathways')).toBeNull()
    expect(screen.queryByText(/Explore civic forecasts/)).toBeNull()
  })
})
