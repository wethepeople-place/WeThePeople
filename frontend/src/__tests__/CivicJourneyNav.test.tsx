import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { expect, it } from 'vitest';
import CivicJourneyNav from '../components/CivicJourneyNav';

it('connects every top-level civic journey destination', () => {
  render(<MemoryRouter initialEntries={['/government']}><CivicJourneyNav /></MemoryRouter>);

  const expected = {
    Watch: '/watch',
    Agenda: '/civic',
    Issues: '/issues/housing-rent',
    Discuss: '/discuss',
    Elections: '/elections',
    Solutions: '/issues/housing-rent/solutions',
    Representatives: '/politics/find-rep',
    ACT: '/act',
  };

  for (const [label, href] of Object.entries(expected)) {
    expect(screen.getAllByRole('link', { name: label })[0].getAttribute('href')).toBe(href);
  }
  expect(screen.getByRole('link', { name: 'Elections' }).getAttribute('href')).toBe('/elections');
  expect(screen.getByRole('link', { name: 'Create a civic post' }).getAttribute('href')).toBe('/discuss?compose=1#composer');
});
