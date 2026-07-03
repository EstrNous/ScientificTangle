import { describe, expect, it } from 'vitest';
import { useThemeStore } from '../stores/themeStore.js';

describe('themeStore', () => {
  it('toggles theme', () => {
    useThemeStore.setState({ theme: 'light' });
    useThemeStore.getState().toggleTheme();
    expect(useThemeStore.getState().theme).toBe('dark');
  });
});
