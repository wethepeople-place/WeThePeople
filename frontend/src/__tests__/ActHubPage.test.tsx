import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import ActHubPage from '../pages/ActHubPage'

describe('ActHubPage', () => {
  afterEach(() => window.history.replaceState({}, '', '/'))

  it('offers supported action destinations and keeps unfinished community features hidden', () => {
    render(<MemoryRouter><ActHubPage /></MemoryRouter>)
    expect(screen.getByRole('heading', { name: 'ACT' })).toBeTruthy()
    expect(screen.getByText((_, element) => element?.tagName === 'P' && element.textContent === 'Don’t like what those old men decide? Change who gets to decide.')).toBeTruthy()
    expect(screen.getByText('If their agenda doesn’t align with yours, vote them out.')).toBeTruthy()
    expect(screen.getByRole('img', { name: /Texas Lieutenant Governor Dan Patrick/ }).getAttribute('src')).toBe('/images/act-dan-patrick-thc-june-2025.png')
    expect(screen.getByTitle('Step 1: Plan my vote').getAttribute('src')).toBe('/elections?embed=1')
    expect(screen.getByTitle('Step 2: Contact my representatives').getAttribute('src')).toBe('/politics/find-rep?embed=1')
    expect(screen.getByRole('link', { name: /Next: contact your representatives/ }).getAttribute('href')).toBe('#act-option-reps')
    expect(screen.getByRole('navigation', { name: 'Your two-step action path' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Choose what you want to do' })).toBeTruthy()
    expect(screen.getByRole('link', { name: /1Start herePlan my voteSee your ballot and polling place/ }).getAttribute('href')).toBe('#act-option-vote')
    expect(screen.getByRole('link', { name: /2Or go hereContact my representativesFind, review, and contact your officials/ }).getAttribute('href')).toBe('#act-option-reps')
    expect(screen.getByText('Step 1 of 2 · Voting')).toBeTruthy()
    expect(screen.getByText('Step 2 of 2 · Representation')).toBeTruthy()
    expect(screen.getByTitle('Step 1: Plan my vote').getAttribute('style')).toContain('height: 560px')
    expect(screen.queryByText('Action Circles')).toBeNull()
    expect(screen.queryByText('Activities')).toBeNull()
    expect(screen.queryByText('About future legal pathways')).toBeNull()
    expect(screen.queryByText(/Explore civic forecasts/)).toBeNull()
  })

  it('scrolls direct voting links to the plan-my-vote section', () => {
    const scrollIntoView = vi.fn()
    window.history.replaceState({}, '', '/act#act-option-vote')
    Element.prototype.scrollIntoView = scrollIntoView

    render(<MemoryRouter><ActHubPage /></MemoryRouter>)

    expect(scrollIntoView).toHaveBeenCalledWith({ block: 'start' })
  })
})
