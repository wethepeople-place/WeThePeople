import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { expect, it } from 'vitest';
import CivicJourneyNav from '../components/CivicJourneyNav';

it('connects every top-level civic journey destination', () => {
  render(<MemoryRouter initialEntries={['/government']}><CivicJourneyNav /></MemoryRouter>);

  const expected = {
    Agenda: '/civic',
    Issues: '/issues/housing-rent',
    Discuss: '/discuss',
    Videos: '/videos',
    Proposals: '/proposals',
    Elections: '/elections',
    Representatives: '/politics/find-rep',
    ACT: '/act',
    Jobs: 'https://research.wethepeople.place/gov-salaries',
    Forecasts: '/forecasts',
  };

  for (const [label, href] of Object.entries(expected)) {
    expect(screen.getAllByRole('link', { name: label })[0].getAttribute('href')).toBe(href);
  }
  expect(screen.getByRole('link', { name: 'Elections' }).getAttribute('href')).toBe('/elections');
  expect(screen.getByRole('link', { name: 'Create a civic post' }).getAttribute('href')).toBe('/discuss?compose=1#composer');
});

it('keeps the six main phone-first destinations directly reachable', () => {
  render(<MemoryRouter><CivicJourneyNav /></MemoryRouter>);
  for (const label of ['Discuss', 'Videos', 'Agenda', 'ACT', 'Reps', 'Forecasts']) {
    expect(screen.getAllByRole('link', { name: label }).length).toBeGreaterThan(0);
  }
  expect(screen.queryByRole('link', { name: 'Community' })).toBeNull();
});
