import { apiGet, apiOptions } from './client.js';
import { mapApiError } from './errors.js';

export async function fetchQueryRun(runId) {
  try {
    return await apiGet(`/runs/${encodeURIComponent(runId)}`, apiOptions());
  } catch (error) {
    throw new Error(mapApiError(error, 'query_run_load_failed'));
  }
}
