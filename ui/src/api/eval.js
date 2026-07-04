import { apiGet, apiOptions } from './client.js';
import { mapApiError } from './errors.js';

export function mapEvalReportSummary(payload = {}) {
  return {
    reportId: payload.report_id ?? payload.reportId ?? '',
    status: payload.status ?? 'warn',
    generatedAt: payload.generated_at ?? payload.generatedAt ?? null,
    suites: payload.suites ?? {},
    metrics: payload.metrics ?? {},
    warnings: payload.warnings ?? [],
    blockedChecks: payload.blocked_checks ?? payload.blockedChecks ?? [],
  };
}

export async function fetchEvalReportSummary() {
  try {
    const payload = await apiGet('/eval/report/summary', apiOptions());
    return mapEvalReportSummary(payload);
  } catch (error) {
    throw new Error(mapApiError(error, 'eval_report_load_failed'));
  }
}
