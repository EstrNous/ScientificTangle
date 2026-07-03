import { apiGet } from './client.js';

const real = { real: true };

export function fetchLabCoverage() {
  return apiGet('/lab/coverage', real);
}
