import { apiGet, apiPost, apiOptions } from './client.js';
import { mapApiError } from './errors.js';
import { mapNotification, mapNotificationList } from './mappers/productApi.js';

export async function fetchNotifications({ since } = {}) {
  try {
    const query = since ? `?since=${encodeURIComponent(since)}` : '';
    const payload = await apiGet(`/notifications${query}`, apiOptions());
    return mapNotificationList(payload);
  } catch (error) {
    throw new Error(mapApiError(error, 'notifications_load_failed'));
  }
}

export async function markNotificationRead(id) {
  try {
    await apiPost(`/notifications/${encodeURIComponent(id)}/read`, {}, apiOptions());
    return { id, read: true };
  } catch (error) {
    throw new Error(mapApiError(error, 'notification_read_failed'));
  }
}

export async function markAllNotificationsRead() {
  try {
    await apiPost('/notifications/read-all', {}, apiOptions());
    return { ok: true };
  } catch (error) {
    throw new Error(mapApiError(error, 'notifications_read_all_failed'));
  }
}

export { mapNotification, mapNotificationList } from './mappers/productApi.js';
