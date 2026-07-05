import axios from 'axios';
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

export function parseHealthHttpResponse(status, data) {
  if ((status === 200 || status === 503) && data) {
    return mapHealthPayload(data);
  }
  return null;
}

export async function fetchServiceHealth() {
  try {
    const payload = await apiGet('/health/all', { real: true });
    return mapHealthPayload(payload);
  } catch (error) {
    if (axios.isAxiosError(error) && error.response) {
      const parsed = parseHealthHttpResponse(error.response.status, error.response.data);
      if (parsed) {
        return parsed;
      }
    }
    throw error;
  }
}
