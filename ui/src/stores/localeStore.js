import { create } from 'zustand';

const defaultLocale = import.meta.env.VITE_DEFAULT_LOCALE || 'ru';

export const useLocaleStore = create((set) => ({
  locale: defaultLocale,
  setLocale: (locale) => set({ locale }),
}));
