import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '../../test/renderWithProviders.jsx';
import DarkModeToggle from './DarkModeToggle.jsx';

describe('DarkModeToggle', () => {
  it('renders toggle button', () => {
    const { getByRole } = renderWithProviders(<DarkModeToggle />);
    expect(getByRole('button')).toBeTruthy();
  });
});
