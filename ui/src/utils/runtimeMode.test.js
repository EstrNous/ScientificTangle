import { afterEach, describe, expect, it, vi } from 'vitest';

describe('runtimeMode', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it('enables mock only when VITE_USE_MOCK is true', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'true');
    const { resolveUseMock } = await import('./runtimeMode.js');
    expect(resolveUseMock()).toBe(true);
  });

  it('disables mock when VITE_USE_MOCK is false', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'false');
    vi.resetModules();
    const { resolveUseMock } = await import('./runtimeMode.js');
    expect(resolveUseMock()).toBe(false);
  });

  it('disables mock when VITE_USE_MOCK is unset', async () => {
    vi.stubEnv('VITE_USE_MOCK', '');
    vi.resetModules();
    const { resolveUseMock } = await import('./runtimeMode.js');
    expect(resolveUseMock()).toBe(false);
  });
});
