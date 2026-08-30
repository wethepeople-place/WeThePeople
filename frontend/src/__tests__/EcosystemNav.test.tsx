import { render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';

import EcosystemNav from '../components/EcosystemNav';

vi.mock('../contexts/AuthContext', () => ({ useAuth: () => ({ isAuthenticated: false }) }));

it('keeps Agenda in the civic menu and groups sibling sites under More', () => {
  render(<EcosystemNav active="core" />);

  expect(screen.queryByRole('link', { name: 'Civic Hub' })).toBeNull();
  expect(screen.getByText('More')).toBeTruthy();
  expect(screen.getByRole('link', { name: 'Verify' }).getAttribute('href')).toBe('https://verify.wethepeople.place');
  expect(screen.getByRole('link', { name: 'Research' }).getAttribute('href')).toBe('https://research.wethepeople.place');
  expect(screen.getByRole('link', { name: 'Journal' }).getAttribute('href')).toBe('https://journal.wethepeople.place');
  expect(screen.getAllByText('WeThePeople')).toHaveLength(1);
});
