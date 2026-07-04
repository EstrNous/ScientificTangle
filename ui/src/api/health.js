import { apiGet } from './client.js';

export function mapHealthPayload(payload) {
  const peers = (payload?.peers ?? []).map((peer) => ({
    service: peer.service,
    status: peer.status ?? 'down',
    httpStatus: peer.http_status ?? null,
    error: peer.error ?? null,
  }));
  const overall = payload?.status ?? 'down';
  return { overall, peers };
}

export async function fetchServiceHealth() {
  const payload = await apiGet('/health/all', { real: true });
  return mapHealthPayload(payload);
}
