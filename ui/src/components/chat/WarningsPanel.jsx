import ReasonCodeBadges from './ReasonCodeBadges.jsx';

export default function WarningsPanel({ confidence, warnings = [] }) {
  const hasWarnings = warnings.length > 0;
  const lowConfidence = confidence != null && confidence < 0.8;

  if (!hasWarnings && !lowConfidence) return null;

  return (
    <div className="space-y-2">
      {lowConfidence && (
        <p className="text-xs text-amber-600 dark:text-amber-400">
          Уверенность ответа: {(confidence * 100).toFixed(0)}% — проверьте источники
        </p>
      )}
      {hasWarnings && (
        <div className="rounded-lg border border-amber-300/70 bg-amber-50/60 px-3 py-2 dark:border-amber-800 dark:bg-amber-950/20">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-amber-800 dark:text-amber-200">
            Предупреждения
          </p>
          <ul className="space-y-1.5">
            {warnings.map((warning, index) => (
              <li key={index} className="text-xs text-amber-900 dark:text-amber-100">
                <p>{warning.statement}</p>
                {warning.reason_codes?.length > 0 && (
                  <ReasonCodeBadges reasonCodes={warning.reason_codes} />
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
