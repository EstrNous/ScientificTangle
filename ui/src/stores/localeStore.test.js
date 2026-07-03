import { describe, expect, it } from 'vitest';
import { useLocaleStore } from '../stores/localeStore.js';

describe('localeStore', () => {
  it('sets locale', () => {
    useLocaleStore.getState().setLocale('en');
    expect(useLocaleStore.getState().locale).toBe('en');
  });
});
