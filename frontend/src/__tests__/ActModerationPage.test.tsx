import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import ActModerationPage from '../pages/ActModerationPage';

vi.mock('../contexts/AuthContext', () => ({ useAuth: () => ({ user: { id: 1, role: 'admin' }, loading: false }) }));

const queue = { total: 1, counts: { circles: 1, activities: 0 }, items: [{
  kind: 'circle', id: 4, moderation_status: 'pending', organizer: { id: 8, display_name: 'Resident' },
  name: 'Housing evidence circle', objective: 'Ask for an official response.',
  description: 'Residents prepare sourced and respectful questions.', target_type: 'bill', target_id: 'hr6644-119',
  membership_mode: 'approval', conduct_rules: 'Use evidence and protect privacy.',
  completion_condition: 'An official response is documented.', created_at: '2026-08-16T00:00:00Z', updated_at: '2026-08-16T00:00:00Z',
}] };

describe('ActModerationPage', () => {
  beforeEach(() => vi.stubGlobal('fetch', vi.fn().mockImplementation((_input: string, init?: RequestInit) => Promise.resolve({ ok: true, json: async () => init?.method === 'PATCH' ? queue.items[0] : queue }))));

  it('shows a privacy-safe queue and requires an auditable reason', async () => {
    render(<MemoryRouter><ActModerationPage /></MemoryRouter>);
    expect(await screen.findByRole('heading', { name: 'Housing evidence circle' })).toBeTruthy();
    expect(screen.queryByText(/identities are never shown/i)).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Publish' }));
    expect(screen.getByRole('alert').textContent).toContain('at least 10 characters');
    fireEvent.change(screen.getByLabelText(/Review reason/), { target: { value: 'Reviewed against the safety checklist.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Publish' }));
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
    expect(await screen.findByText(/published with an audit record/i)).toBeTruthy();
  });
});
