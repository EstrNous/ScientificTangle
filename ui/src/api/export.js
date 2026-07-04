import { apiPost, apiOptions } from './client.js';
import { mapApiError } from './errors.js';
import { mapExportPayload, serializeExportRequest } from './mappers/productApi.js';

export async function requestExport({ queryRunId, format = 'markdown' }) {
  try {
    const payload = await apiPost('/export', serializeExportRequest({ queryRunId, format }), apiOptions());
    return mapExportPayload(payload);
  } catch (error) {
    throw new Error(mapApiError(error, 'export_failed'));
  }
}

export { mapExportPayload } from './mappers/productApi.js';
