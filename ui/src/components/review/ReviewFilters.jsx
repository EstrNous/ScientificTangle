import { useTranslation } from 'react-i18next';

const STATUS_OPTIONS = ['', 'pending', 'approved', 'rejected', 'deferred'];
const TYPE_OPTIONS = ['', 'substance', 'process_term', 'numeric_claim', 'entity'];

export default function ReviewFilters({ filters, onChange }) {
  const { t } = useTranslation();

  const setField = (field, value) => {
    onChange({ ...filters, [field]: value || null });
  };

  return (
    <div className="flex flex-wrap items-end gap-3 border-b border-nn-border pb-4 dark:border-slate-700">
      <label className="flex min-w-[9rem] flex-col gap-1 text-xs">
        <span className="font-medium text-nn-gray dark:text-slate-400">{t('review.filters.status')}</span>
        <select
          value={filters.status ?? ''}
          onChange={(event) => setField('status', event.target.value)}
          className="rounded-lg border border-nn-border bg-white px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-900"
        >
          {STATUS_OPTIONS.map((value) => (
            <option key={value || 'all'} value={value}>
              {value ? t(`review.status.${value}`) : t('review.filters.all')}
            </option>
          ))}
        </select>
      </label>
      <label className="flex min-w-[9rem] flex-col gap-1 text-xs">
        <span className="font-medium text-nn-gray dark:text-slate-400">{t('review.filters.type')}</span>
        <select
          value={filters.type ?? ''}
          onChange={(event) => setField('type', event.target.value)}
          className="rounded-lg border border-nn-border bg-white px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-900"
        >
          {TYPE_OPTIONS.map((value) => (
            <option key={value || 'all'} value={value}>
              {value ? t(`review.types.${value}`, { defaultValue: value }) : t('review.filters.all')}
            </option>
          ))}
        </select>
      </label>
      <label className="flex min-w-[10rem] flex-col gap-1 text-xs">
        <span className="font-medium text-nn-gray dark:text-slate-400">{t('review.filters.from')}</span>
        <input
          type="date"
          value={filters.from ?? ''}
          onChange={(event) => setField('from', event.target.value)}
          className="rounded-lg border border-nn-border bg-white px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-900"
        />
      </label>
      <label className="flex min-w-[10rem] flex-col gap-1 text-xs">
        <span className="font-medium text-nn-gray dark:text-slate-400">{t('review.filters.to')}</span>
        <input
          type="date"
          value={filters.to ?? ''}
          onChange={(event) => setField('to', event.target.value)}
          className="rounded-lg border border-nn-border bg-white px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-900"
        />
      </label>
    </div>
  );
}
