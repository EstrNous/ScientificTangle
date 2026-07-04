import { apiGet, apiOptions } from './client.js';
import { mapApiError } from './errors.js';

export function buildAuditEventsQuery({ action, userId, limit = 200, offset = 0 } = {}) {
  const params = new URLSearchParams();
  params.set('limit', String(limit));
  params.set('offset', String(offset));
  if (action) {
    params.set('action', action);
  }
  if (userId) {
    params.set('user_id', String(userId));
  }
  return `?${params.toString()}`;
}

export async function fetchAuditEvents(filters = {}) {
  try {
    const query = buildAuditEventsQuery(filters);
    const payload = await apiGet(`/audit/events${query}`, apiOptions());
    return Array.isArray(payload) ? payload : payload?.items ?? [];
  } catch (error) {
    throw new Error(mapApiError(error, 'audit_load_failed'));
  }
}
