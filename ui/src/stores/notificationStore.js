import { create } from 'zustand';

export const useNotificationStore = create((set) => ({
  items: [],
  unreadCount: 0,
  setItems: (items) =>
    set({
      items,
      unreadCount: items.filter((n) => !n.read).length,
    }),
  markAllRead: () =>
    set((state) => ({
      items: state.items.map((n) => ({ ...n, read: true })),
      unreadCount: 0,
    })),
}));
