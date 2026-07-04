import { apiGet, apiPost } from './client.js';

const real = { real: true };

export async function fetchNotifications() {
  return apiGet('/notifications', real);
}

export async function markNotificationRead(id) {
  return apiPost(`/notifications/${id}/read`, {}, real);
}

export async function markAllNotificationsRead() {
  return apiPost('/notifications/read-all', {}, real);
}
