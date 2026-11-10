import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { expect, it } from 'vitest';
import CivicJourneyNav from '../components/CivicJourneyNav';

it('connects the simplified civic journey destinations', () => {
  render(<MemoryRouter initialEntries={['/government']}><CivicJourneyNav /></MemoryRouter>);

  const expected = {
    Agenda: '/civic',
    Watch: '/videos',
    Issues: '/issues/housing-rent',
    Elections: '/elections',
    ACT: '/act',
    Jobs: 'https://research.wethepeople.place/gov-salaries',
    Bets: '/forecasts',
  };

  for (const [label, href] of Object.entries(expected)) {
    expect(screen.getAllByRole('link', { name: label })[0].getAttribute('href')).toBe(href);
  }
  expect(screen.queryByRole('link', { name: 'Discuss' })).toBeNull();
  expect(screen.queryByRole('link', { name: 'Post' })).toBeNull();
  expect(screen.queryByRole('link', { name: 'Solutions' })).toBeNull();
  expect(screen.queryByRole('link', { name: 'Representatives' })).toBeNull();
  expect(screen.getByRole('link', { name: 'Reps' }).getAttribute('href')).toBe('/politics/find-rep');
});

it('keeps the same bottom dock visible on elections', () => {
  render(<MemoryRouter initialEntries={['/elections']}><CivicJourneyNav /></MemoryRouter>);
  const dock = screen.getByRole('navigation', { name: 'Primary' });
  expect(dock.className).toContain('fixed');
  expect(dock.className).not.toContain('md:hidden');
  expect(screen.getAllByRole('link', { name: 'Elections' })[1].getAttribute('aria-current')).toBe('page');
});

it('keeps all seven simple destinations directly reachable', () => {
  render(<MemoryRouter><CivicJourneyNav /></MemoryRouter>);
  for (const label of ['Agenda', 'Watch', 'Elections', 'ACT', 'Reps', 'Jobs', 'Bets']) {
    expect(screen.getAllByRole('link', { name: label }).length).toBeGreaterThan(0);
  }
});
