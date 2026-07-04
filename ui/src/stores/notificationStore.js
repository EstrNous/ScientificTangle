import { create } from 'zustand';

function countUnread(items) {
  return items.filter((item) => !item.read).length;
}

export const useNotificationStore = create((set) => ({
  items: [],
  unreadCount: 0,
  loading: false,
  setLoading: (loading) => set({ loading }),
  setItems: (items) =>
    set({
      items,
      unreadCount: countUnread(items),
    }),
  markRead: (id) =>
    set((state) => {
      const items = state.items.map((item) =>
        item.id === id ? { ...item, read: true } : item,
      );
      return { items, unreadCount: countUnread(items) };
    }),
  markAllRead: () =>
    set((state) => ({
      items: state.items.map((item) => ({ ...item, read: true })),
      unreadCount: 0,
    })),
}));
