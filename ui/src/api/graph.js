import { apiGet } from './client.js';

const real = { real: true };

export function fetchGraphData() {
  return apiGet('/graph', real);
}

export function fetchSearchCatalog() {
  return apiGet('/search', real);
}
