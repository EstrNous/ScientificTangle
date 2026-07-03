import { apiGet } from './client.js';

const real = { real: true };

export function fetchStrategicMetrics() {
  return apiGet('/strategic/metrics', real);
}

export function fetchStrategicEvaluation() {
  return apiGet('/strategic/evaluation', real);
}
