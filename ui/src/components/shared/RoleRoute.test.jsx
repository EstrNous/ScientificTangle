import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '../../test/renderWithProviders.jsx';
import RoleRoute from './RoleRoute.jsx';

describe('RoleRoute', () => {
  it('renders children when role allowed', () => {
    const { getByText } = renderWithProviders(
      <RoleRoute paths={['chat']}>
        <span>allowed</span>
      </RoleRoute>,
      { role: 'director' },
    );
    expect(getByText('allowed')).toBeTruthy();
  });
});
