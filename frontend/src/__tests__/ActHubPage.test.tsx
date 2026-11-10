import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import ActHubPage from '../pages/ActHubPage'

describe('ActHubPage', () => {
  it('offers supported action destinations and keeps unfinished community features hidden', () => {
    render(<MemoryRouter><ActHubPage /></MemoryRouter>)
    expect(screen.getByRole('heading', { name: 'ACT' })).toBeTruthy()
    expect(screen.getByText((_, element) => element?.tagName === 'P' && element.textContent === 'Don’t like what those old men decide? Change who gets to decide.')).toBeTruthy()
    expect(screen.getByText('If their agenda doesn’t align with yours, vote them out.')).toBeTruthy()
    expect(screen.getByTitle('Step 1: Plan my vote').getAttribute('src')).toBe('/elections?embed=1')
    expect(screen.getByTitle('Step 2: Contact my representatives').getAttribute('src')).toBe('/politics/find-rep?embed=1')
    expect(screen.getByRole('link', { name: /Next: contact your representatives/ }).getAttribute('href')).toBe('#act-option-reps')
    expect(screen.getByTitle('Step 1: Plan my vote').getAttribute('style')).toContain('height: 560px')
    expect(screen.queryByText('Action Circles')).toBeNull()
    expect(screen.queryByText('Activities')).toBeNull()
    expect(screen.queryByText('About future legal pathways')).toBeNull()
    expect(screen.queryByText(/Explore civic forecasts/)).toBeNull()
  })
})
