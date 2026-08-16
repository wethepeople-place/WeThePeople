import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { expect, it } from 'vitest';
import CivicJourneyNav from '../components/CivicJourneyNav';

it('connects every top-level civic journey destination', () => {
  render(<MemoryRouter initialEntries={['/government']}><CivicJourneyNav /></MemoryRouter>);

  const expected = {
    Watch: '/watch',
    Agenda: '/civic',
    Evidence: '/issues/housing-rent',
    Government: '/government',
    Courts: '/courts',
    Discuss: '/discuss',
    Solutions: '/issues/housing-rent/solutions',
    'Your District': '/politics/find-rep',
    ACT: '/act',
  };

  for (const [label, href] of Object.entries(expected)) {
    expect(screen.getByRole('link', { name: label }).getAttribute('href')).toBe(href);
  }
  expect(screen.getByRole('link', { name: 'Government' }).getAttribute('aria-current')).toBe('page');
});
