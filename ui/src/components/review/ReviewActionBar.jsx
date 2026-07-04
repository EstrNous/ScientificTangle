import { useTranslation } from 'react-i18next';
import { isReviewActionsEnabled } from '../../utils/uiFeatureFlags.js';

const DECISIONS = ['approved', 'rejected', 'deferred'];

export default function ReviewActionBar({ candidate, loading, onDecision }) {
  const { t } = useTranslation();
  const actionsEnabled = isReviewActionsEnabled();

  if (!candidate) {
    return null;
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-nn-border pt-4 dark:border-slate-700">
      <div className="min-w-0">
        <p className="text-sm font-semibold text-gray-900 dark:text-slate-100">{candidate.name}</p>
        {!actionsEnabled && (
          <p className="mt-1 text-xs text-nn-gray dark:text-slate-400">{t('review.actionsBlocked')}</p>
        )}
      </div>
      <div className="flex flex-wrap gap-2">
        {DECISIONS.map((decision) => (
          <button
            key={decision}
            type="button"
            disabled={!actionsEnabled || loading || candidate.status !== 'pending'}
            onClick={() => onDecision(decision)}
            className="rounded-lg border border-nn-border px-3 py-1.5 text-xs font-medium text-gray-800 transition-colors hover:bg-nn-gray-light disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-600 dark:text-slate-100 dark:hover:bg-slate-800"
          >
            {t(`review.decisions.${decision}`)}
          </button>
        ))}
      </div>
    </div>
  );
}
