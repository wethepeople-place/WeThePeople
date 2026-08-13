import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { PoliticsSectorHeader } from '../components/SectorHeader';

describe('SectorHeader mobile containment', () => {
  it('constrains the tab row to the remaining header width', () => {
    const { container } = render(<MemoryRouter><PoliticsSectorHeader /></MemoryRouter>);
    const navigation = container.querySelector('nav');
    const tabRow = navigation?.lastElementChild;

    expect(navigation?.className).toContain('min-w-0');
    expect(navigation?.className).toContain('px-4');
    expect(tabRow?.className).toContain('min-w-0');
    expect(tabRow?.className).toContain('flex-1');
    expect(tabRow?.className).toContain('overflow-x-auto');
    expect(tabRow?.className).not.toContain('shrink-0');
  });
});
