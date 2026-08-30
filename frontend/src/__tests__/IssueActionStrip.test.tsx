import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import IssueActionStrip from '../components/IssueActionStrip';

describe('IssueActionStrip', () => {
  it('keeps every civic action scoped to the issue', () => {
    const { container } = render(<MemoryRouter><IssueActionStrip issueSlug="housing-rent" returnToVideoId="housing-video" /></MemoryRouter>);

    expect(screen.getByRole('navigation', { name: 'Issue actions' })).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Evidence' }).getAttribute('href')).toBe('/issues/housing-rent#evidence');
    expect(screen.getByRole('link', { name: 'Bills' }).getAttribute('href')).toBe('/issues/housing-rent#legislation');
    expect(screen.getByRole('link', { name: 'Community' }).getAttribute('href')).toBe('/discuss?issue=housing-rent');
    expect(screen.queryByRole('link', { name: 'Solutions' })).toBeNull();
    expect(screen.queryByRole('link', { name: 'Discuss' })).toBeNull();
    expect(screen.getByRole('link', { name: 'Government' }).getAttribute('href')).toBe('/government?issue=housing-rent');
    expect(screen.getByRole('link', { name: 'Representatives' }).getAttribute('href')).toBe('/politics/find-rep?issue=housing-rent');
    expect(screen.getByRole('link', { name: 'Courts' }).getAttribute('href')).toBe('/courts?issue=housing-rent');
    expect(screen.getByRole('link', { name: 'ACT' }).getAttribute('href')).toBe('/act?target_type=video&target_id=housing-video');
    expect(container.querySelector('nav')?.className).toContain('grid-cols-2');
    expect(container.querySelector('nav')?.className).toContain('sm:grid-cols-4');
    expect(container.querySelector('nav')?.className).not.toContain('overflow-x-auto');
  });
});
