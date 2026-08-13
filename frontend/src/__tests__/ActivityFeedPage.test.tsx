import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import ActivityFeedPage from '../pages/ActivityFeedPage';

vi.mock('../components/SectorHeader', () => ({ PoliticsSectorHeader: () => null }));
vi.mock('../api/client', () => ({
  apiClient: {
    getRecentActions: vi.fn().mockResolvedValue([]),
    getVotes: vi.fn().mockResolvedValue({ votes: [] }),
  },
}));

describe('ActivityFeedPage responsive containment', () => {
  it('uses responsive grid hooks instead of a fixed inline sidebar column', async () => {
    const { container } = render(
      <MemoryRouter>
        <ActivityFeedPage />
      </MemoryRouter>,
    );

    const grid = await screen.findByTestId('activity-feed-grid');
    expect(grid.className).toContain('activity-feed-grid');
    expect(grid.getAttribute('style') || '').not.toContain('grid-template-columns');
    expect(container.querySelector('.activity-content-wrap')).toBeTruthy();
    expect(container.querySelector('.activity-timeline')).toBeTruthy();
    expect(container.querySelector('.activity-votes-sidebar')).toBeTruthy();
  });
});
