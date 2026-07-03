import { describe, expect, it } from 'vitest';
import { useNotificationStore } from '../stores/notificationStore.js';

describe('notificationStore', () => {
  it('computes unread count', () => {
    useNotificationStore.getState().setItems([
      { id: '1', read: false },
      { id: '2', read: true },
    ]);
    expect(useNotificationStore.getState().unreadCount).toBe(1);
    useNotificationStore.getState().markAllRead();
    expect(useNotificationStore.getState().unreadCount).toBe(0);
  });
});
