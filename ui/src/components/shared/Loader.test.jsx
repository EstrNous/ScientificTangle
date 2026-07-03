import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../test/renderWithProviders.jsx';
import Loader from '../components/shared/Loader.jsx';

describe('Loader', () => {
  it('renders', () => {
    const { container } = renderWithProviders(<Loader />);
    expect(container.firstChild).toBeTruthy();
  });
});
