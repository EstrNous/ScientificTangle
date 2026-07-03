import { create } from 'zustand';
import { persist } from 'zustand/middleware';

function applyTheme(theme) {
  document.documentElement.classList.toggle('dark', theme === 'dark');
}

export const useThemeStore = create(
  persist(
    (set, get) => ({
      theme: 'light',
      toggleTheme: () => {
        const next = get().theme === 'light' ? 'dark' : 'light';
        set({ theme: next });
        applyTheme(next);
      },
    }),
    {
      name: 'nn-theme',
      onRehydrateStorage: () => (state) => {
        if (state?.theme) applyTheme(state.theme);
      },
    }
  )
);

export function initThemeFromStorage() {
  try {
    const raw = localStorage.getItem('nn-theme');
    if (!raw) return;
    const theme = JSON.parse(raw)?.state?.theme;
    if (theme === 'dark' || theme === 'light') applyTheme(theme);
  } catch {
    applyTheme('light');
  }
}
