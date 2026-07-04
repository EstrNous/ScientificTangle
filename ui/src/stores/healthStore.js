import { create } from 'zustand';
import { fetchServiceHealth } from '../api/health.js';
import { useMock } from '../api/client.js';

const POLL_MS = 60000;

export const useHealthStore = create((set) => ({
  overall: null,
  peers: [],
  loading: false,
  error: null,
  lastChecked: null,
  refresh: async () => {
    if (useMock) {
      set({ overall: null, peers: [], loading: false, error: null, lastChecked: null });
      return;
    }
    set({ loading: true, error: null });
    try {
      const health = await fetchServiceHealth();
      set({
        overall: health.overall,
        peers: health.peers,
        loading: false,
        error: null,
        lastChecked: Date.now(),
      });
    } catch (loadError) {
      set({
        loading: false,
        error: loadError instanceof Error ? loadError.message : 'health_check_failed',
        lastChecked: Date.now(),
      });
    }
  },
}));

let pollTimer = null;

export function startHealthPolling() {
  if (useMock) {
    return () => {};
  }
  const { refresh } = useHealthStore.getState();
  refresh();
  pollTimer = window.setInterval(refresh, POLL_MS);
  return () => {
    if (pollTimer != null) {
      window.clearInterval(pollTimer);
      pollTimer = null;
    }
  };
}
