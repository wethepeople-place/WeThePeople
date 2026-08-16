import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import RepresentativeActPanel from '../components/RepresentativeActPanel'

vi.mock('../contexts/AuthContext', () => ({ useAuth: () => ({ isAuthenticated: false }) }))

describe('RepresentativeActPanel', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        representative: { person_id: 'rep-example', display_name: 'Representative Example', chamber: 'house', state: 'MD', party: 'I' },
        contacts: [{ id: 1, office_type: 'district', label: 'District office', phone: '301-555-0100', contact_url: null, address: null, source: { publisher: 'U.S. House', url: 'https://example.house.gov/contact' }, verification_status: 'verified', retrieved_at: '2026-08-15T00:00:00Z', verified_at: '2026-08-15T00:00:00Z' }, { id: 2, office_type: 'contact_form', label: 'Official contact form', phone: null, contact_url: 'https://example.house.gov/contact', address: null, source: { publisher: 'U.S. House', url: 'https://example.house.gov/contact' }, verification_status: 'verified', retrieved_at: '2026-08-15T00:00:00Z', verified_at: '2026-08-15T00:00:00Z' }],
        fallback: { label: 'U.S. Capitol Switchboard', phone: '202-224-3121', source: { publisher: 'U.S. Senate', url: 'https://www.senate.gov/senators/senators-contact.htm' } },
        message_policy: { auto_send: false, delivery_claimed: false, instructions: 'Review and submit it yourself.' },
      }),
    }))
  })

  it('shows verified public contact routes and never claims to send the message', async () => {
    render(<MemoryRouter><RepresentativeActPanel personId="rep-example" displayName="Representative Example" issueSlug="housing-rent" /></MemoryRouter>)
    fireEvent.click(screen.getByRole('button', { name: 'ACT: contact office' }))
    expect(await screen.findByRole('dialog', { name: 'Contact Representative Example' })).toBeTruthy()
    expect(screen.getByRole('link', { name: /District office/ }).getAttribute('href')).toBe('tel:301-555-0100')
    expect(screen.getByRole('link', { name: /U.S. Capitol Switchboard/ }).getAttribute('href')).toBe('tel:202-224-3121')
    expect(screen.getByRole('link', { name: 'Open Official contact form' }).getAttribute('href')).toBe('https://example.house.gov/contact')
    expect(screen.getByDisplayValue(/housing rent/)).toBeTruthy()
    expect(screen.getByText(/never sends messages or places calls/i)).toBeTruthy()
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1))
  })
})
