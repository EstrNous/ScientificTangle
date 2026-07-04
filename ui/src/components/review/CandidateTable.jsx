import { useTranslation } from 'react-i18next';

const STATUS_STYLES = {
  pending: 'bg-amber-100 text-amber-900 dark:bg-amber-500/20 dark:text-amber-100',
  approved: 'bg-emerald-100 text-emerald-900 dark:bg-emerald-500/20 dark:text-emerald-100',
  rejected: 'bg-red-100 text-red-900 dark:bg-red-500/20 dark:text-red-100',
  deferred: 'bg-slate-200 text-slate-800 dark:bg-slate-700 dark:text-slate-100',
};

export default function CandidateTable({ items, selectedId, onSelect }) {
  const { t } = useTranslation();

  if (!items.length) {
    return (
      <p className="py-8 text-center text-sm text-nn-gray dark:text-slate-400">{t('review.emptyQueue')}</p>
    );
  }

  return (
    <div className="min-h-0 flex-1 overflow-auto">
      <table className="min-w-full text-left text-sm">
        <thead className="sticky top-0 z-10 bg-white text-xs uppercase tracking-wide text-nn-gray dark:bg-slate-900 dark:text-slate-400">
          <tr>
            <th className="px-3 py-2 font-medium">{t('review.columns.name')}</th>
            <th className="px-3 py-2 font-medium">{t('review.columns.type')}</th>
            <th className="px-3 py-2 font-medium">{t('review.columns.status')}</th>
            <th className="px-3 py-2 font-medium">{t('review.columns.confidence')}</th>
            <th className="px-3 py-2 font-medium">{t('review.columns.conflicts')}</th>
            <th className="px-3 py-2 font-medium">{t('review.columns.updated')}</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const selected = item.id === selectedId;
            return (
              <tr
                key={item.id}
                onClick={() => onSelect(item.id)}
                className={`cursor-pointer border-t border-nn-border transition-colors dark:border-slate-700 ${
                  selected ? 'bg-nn-blue-light/70 dark:bg-sky-950/40' : 'hover:bg-nn-gray-light dark:hover:bg-slate-800/60'
                }`}
              >
                <td className="px-3 py-2 font-medium text-gray-900 dark:text-slate-100">{item.name}</td>
                <td className="px-3 py-2 text-nn-gray dark:text-slate-400">
                  {t(`review.types.${item.type}`, { defaultValue: item.type })}
                </td>
                <td className="px-3 py-2">
                  <span
                    className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
                      STATUS_STYLES[item.status] ?? STATUS_STYLES.pending
                    }`}
                  >
                    {t(`review.status.${item.status}`, { defaultValue: item.status })}
                  </span>
                </td>
                <td className="px-3 py-2 tabular-nums text-nn-gray dark:text-slate-400">
                  {Math.round((item.confidence ?? 0) * 100)}%
                </td>
                <td className="px-3 py-2 tabular-nums text-nn-gray dark:text-slate-400">
                  {item.conflictIds?.length ?? 0}
                </td>
                <td className="px-3 py-2 text-xs text-nn-gray dark:text-slate-400">
                  {item.updatedAt ? new Date(item.updatedAt).toLocaleString() : '—'}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
