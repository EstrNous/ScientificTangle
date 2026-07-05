export function resolveUseMock() {
  return import.meta.env.VITE_USE_MOCK === 'true';
}

export const useMock = resolveUseMock();
