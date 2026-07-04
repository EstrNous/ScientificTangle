import { useTranslation } from 'react-i18next';

const SOURCE_TYPE_OPTIONS = ['text', 'table', 'figure', 'caption'];

export default function SearchFilters({ filters, onChange, disabled = false }) {
  const { t } = useTranslation();

  const update = (patch) => onChange({ ...filters, ...patch });

  const toggleSourceType = (value) => {
    const current = filters.sourceTypes ?? [];
    const next = current.includes(value)
      ? current.filter((item) => item !== value)
      : [...current, value];
    update({ sourceTypes: next });
  };

  return (
    <div className="grid gap-3 rounded-xl border border-nn-border bg-white p-4 dark:border-slate-700 dark:bg-slate-900 md:grid-cols-2 xl:grid-cols-4">
      <label className="flex flex-col gap-1 text-xs">
        <span className="font-medium text-nn-gray dark:text-slate-400">{t('search.filters.geo')}</span>
        <input
          value={filters.geoText ?? ''}
          disabled={disabled}
          onChange={(event) => update({ geoText: event.target.value })}
          placeholder={t('search.filters.geoPlaceholder')}
          className="rounded-lg border border-nn-border px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800"
        />
      </label>

      <label className="flex flex-col gap-1 text-xs">
        <span className="font-medium text-nn-gray dark:text-slate-400">{t('search.filters.yearFrom')}</span>
        <input
          type="number"
          value={filters.yearFrom ?? ''}
          disabled={disabled}
          onChange={(event) => update({ yearFrom: event.target.value })}
          placeholder="2020"
          className="rounded-lg border border-nn-border px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800"
        />
      </label>

      <label className="flex flex-col gap-1 text-xs">
        <span className="font-medium text-nn-gray dark:text-slate-400">{t('search.filters.yearTo')}</span>
        <input
          type="number"
          value={filters.yearTo ?? ''}
          disabled={disabled}
          onChange={(event) => update({ yearTo: event.target.value })}
          placeholder="2026"
          className="rounded-lg border border-nn-border px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800"
        />
      </label>

      <div className="flex flex-col gap-1 text-xs">
        <span className="font-medium text-nn-gray dark:text-slate-400">{t('search.filters.numeric')}</span>
        <div className="flex gap-2">
          <input
            type="number"
            value={filters.numericValue ?? ''}
            disabled={disabled}
            onChange={(event) => update({ numericValue: event.target.value })}
            placeholder="82"
            className="w-1/2 rounded-lg border border-nn-border px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800"
          />
          <input
            value={filters.numericUnit ?? ''}
            disabled={disabled}
            onChange={(event) => update({ numericUnit: event.target.value })}
            placeholder="%"
            className="w-1/2 rounded-lg border border-nn-border px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800"
          />
        </div>
      </div>

      <div className="md:col-span-2 xl:col-span-4">
        <p className="mb-2 text-xs font-medium text-nn-gray dark:text-slate-400">
          {t('search.filters.sourceTypes')}
        </p>
        <div className="flex flex-wrap gap-2">
          {SOURCE_TYPE_OPTIONS.map((value) => {
            const active = (filters.sourceTypes ?? []).includes(value);
            return (
              <button
                key={value}
                type="button"
                disabled={disabled}
                onClick={() => toggleSourceType(value)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                  active
                    ? 'bg-nn-blue text-white dark:bg-sky-500'
                    : 'border border-nn-border bg-white text-gray-800 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100'
                }`}
              >
                {t(`search.sourceTypes.${value}`, { defaultValue: value })}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
