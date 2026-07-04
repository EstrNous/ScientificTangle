import { describe, expect, it } from 'vitest';
import { isDevRoleSwitcherEnabled } from './uiFeatureFlags.js';

describe('uiFeatureFlags', () => {
  it('exposes dev role switcher gate', () => {
    expect(typeof isDevRoleSwitcherEnabled()).toBe('boolean');
  });
});
