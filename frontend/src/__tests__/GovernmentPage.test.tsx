import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { expect, it } from 'vitest';
import GovernmentPage from '../pages/GovernmentPage';

it('assembles the existing government and legal activity routes', () => {
  render(<MemoryRouter><GovernmentPage /></MemoryRouter>);

  expect(screen.getByRole('heading', { name: 'Public decisions and responsible institutions' })).toBeTruthy();
  expect(screen.getByRole('link', { name: /Explore legislation/ }).getAttribute('href')).toBe('/politics/legislation');
  expect(screen.getByRole('link', { name: /Explore votes and activity/ }).getAttribute('href')).toBe('/politics/activity');
  expect(screen.getByRole('link', { name: /Explore committees/ }).getAttribute('href')).toBe('/politics/committees');
  expect(screen.getByRole('link', { name: 'Explore Courts' }).getAttribute('href')).toBe('/courts');
});
