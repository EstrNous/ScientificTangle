import { create } from 'zustand';

function countUnread(items) {
  return items.filter((item) => !item.read).length;
}

export const useNotificationStore = create((set) => ({
  items: [],
  unreadCount: 0,
  loading: false,
  lastPolledAt: null,
  setLoading: (loading) => set({ loading }),
  setItems: (items) =>
    set({
      items,
      unreadCount: countUnread(items),
      lastPolledAt: new Date().toISOString(),
    }),
  mergeItems: (incoming) =>
    set((state) => {
      const known = new Set(state.items.map((item) => item.id));
      const merged = [...state.items];
      incoming.forEach((item) => {
        if (known.has(item.id)) {
          const index = merged.findIndex((entry) => entry.id === item.id);
          merged[index] = { ...merged[index], ...item };
        } else {
          merged.unshift(item);
        }
      });
      merged.sort((a, b) => {
        const aTime = new Date(a.createdAt ?? a.created_at ?? 0).getTime();
        const bTime = new Date(b.createdAt ?? b.created_at ?? 0).getTime();
        return bTime - aTime;
      });
      return {
        items: merged,
        unreadCount: countUnread(merged),
        lastPolledAt: new Date().toISOString(),
      };
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
