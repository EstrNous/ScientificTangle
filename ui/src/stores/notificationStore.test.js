import { describe, expect, it } from 'vitest';
import { useNotificationStore } from '../stores/notificationStore.js';

describe('notificationStore', () => {
  it('computes unread count', () => {
    useNotificationStore.getState().setItems([
      { id: '1', read: false },
      { id: '2', read: true },
    ]);
    expect(useNotificationStore.getState().unreadCount).toBe(1);
    useNotificationStore.getState().markRead('1');
    expect(useNotificationStore.getState().unreadCount).toBe(0);
    useNotificationStore.getState().markAllRead();
    expect(useNotificationStore.getState().unreadCount).toBe(0);
  });

  it('merges incoming notifications and updates unread count', () => {
    useNotificationStore.getState().setItems([{ id: '1', read: true }]);
    useNotificationStore.getState().mergeItems([
      { id: '2', read: false, createdAt: '2026-07-04T10:00:00Z' },
    ]);
    expect(useNotificationStore.getState().items).toHaveLength(2);
    expect(useNotificationStore.getState().unreadCount).toBe(1);
  });
});
