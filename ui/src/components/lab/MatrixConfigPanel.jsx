import { useTranslation } from 'react-i18next';
import { LAB_MATRIX_AXIS_TYPES, createMatrixConfig } from './labMatrixTypes.js';

export { createMatrixConfig, applyMatrixConfig } from './labMatrixTypes.js';

const selectClass =
  'w-full min-w-[9rem] rounded-lg border border-nn-border bg-white px-3 py-1.5 text-xs text-gray-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100';

function axisLabel(t, type) {
  return t(`lab.nodeTypes.${type}`, { defaultValue: type });
}

export default function MatrixConfigPanel({ matrixView, config, onChange, availablePairs }) {
  const { t } = useTranslation();

  if (!matrixView) return null;

  const pairAvailable = (rowAxis, colAxis) =>
    availablePairs?.includes(`${rowAxis}_${colAxis}`) ?? false;

  const matrixRows = matrixView.rows ?? [];
  const matrixCols = matrixView.cols ?? [];

  const isFiltered = config.rowFilter !== 'all' || config.colFilter !== 'all';
  const rowCount = config.rowFilter === 'all' ? matrixRows.length : 1;
  const colCount = config.colFilter === 'all' ? matrixCols.length : 1;

  const handleAxisChange = (field, value) => {
    const next = { ...config, [field]: value };
    if (field === 'rowAxis' || field === 'colAxis') {
      if (next.rowAxis === next.colAxis) return;
      if (!pairAvailable(next.rowAxis, next.colAxis)) return;
      next.rowFilter = 'all';
      next.colFilter = 'all';
    }
    onChange(next);
  };

  const reset = () => {
    onChange({
      ...createMatrixConfig(),
      rowAxis: config.rowAxis,
      colAxis: config.colAxis,
    });
  };

  return (
    <div className="nn-card shrink-0 p-3">
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-[10rem] flex-1">
          <label
            htmlFor="matrix-row-axis"
            className="mb-1 block text-[10px] font-medium uppercase tracking-wide text-nn-gray dark:text-slate-400"
          >
            {t('lab.matrixConfig.rowAxis')}
          </label>
          <select
            id="matrix-row-axis"
            value={config.rowAxis}
            onChange={(e) => handleAxisChange('rowAxis', e.target.value)}
            className={selectClass}
          >
            {LAB_MATRIX_AXIS_TYPES.map((type) => (
              <option
                key={type}
                value={type}
                disabled={type === config.colAxis || !pairAvailable(type, config.colAxis)}
              >
                {axisLabel(t, type)}
              </option>
            ))}
          </select>
        </div>

        <div className="min-w-[10rem] flex-1">
          <label
            htmlFor="matrix-col-axis"
            className="mb-1 block text-[10px] font-medium uppercase tracking-wide text-nn-gray dark:text-slate-400"
          >
            {t('lab.matrixConfig.colAxis')}
          </label>
          <select
            id="matrix-col-axis"
            value={config.colAxis}
            onChange={(e) => handleAxisChange('colAxis', e.target.value)}
            className={selectClass}
          >
            {LAB_MATRIX_AXIS_TYPES.map((type) => (
              <option
                key={type}
                value={type}
                disabled={type === config.rowAxis || !pairAvailable(config.rowAxis, type)}
              >
                {axisLabel(t, type)}
              </option>
            ))}
          </select>
        </div>

        <div className="min-w-[10rem] flex-1">
          <label
            htmlFor="matrix-row-filter"
            className="mb-1 block text-[10px] font-medium uppercase tracking-wide text-nn-gray dark:text-slate-400"
          >
            {t('lab.matrixConfig.rowFilter', { type: axisLabel(t, matrixView.rowType) })}
          </label>
          <select
            id="matrix-row-filter"
            value={config.rowFilter}
            onChange={(e) => onChange({ ...config, rowFilter: e.target.value })}
            className={selectClass}
          >
            <option value="all">{t('lab.matrixConfig.allRows')}</option>
            {matrixRows.map((row) => (
              <option key={row} value={row}>
                {row}
              </option>
            ))}
          </select>
        </div>

        <div className="min-w-[10rem] flex-1">
          <label
            htmlFor="matrix-col-filter"
            className="mb-1 block text-[10px] font-medium uppercase tracking-wide text-nn-gray dark:text-slate-400"
          >
            {t('lab.matrixConfig.colFilter', { type: axisLabel(t, matrixView.colType) })}
          </label>
          <select
            id="matrix-col-filter"
            value={config.colFilter}
            onChange={(e) => onChange({ ...config, colFilter: e.target.value })}
            className={selectClass}
          >
            <option value="all">{t('lab.matrixConfig.allCols')}</option>
            {matrixCols.map((col) => (
              <option key={col} value={col}>
                {col}
              </option>
            ))}
          </select>
        </div>

        <div className="min-w-[10rem] flex-1">
          <label
            htmlFor="matrix-filter-display"
            className="mb-1 block text-[10px] font-medium uppercase tracking-wide text-nn-gray dark:text-slate-400"
          >
            {t('lab.matrixConfig.display')}
          </label>
          <select
            id="matrix-filter-display"
            value={config.showValues ? 'always' : 'hover'}
            onChange={(e) =>
              onChange({ ...config, showValues: e.target.value === 'always' })
            }
            className={selectClass}
          >
            <option value="hover">{t('lab.matrixConfig.displayHover')}</option>
            <option value="always">{t('lab.matrixConfig.displayAlways')}</option>
          </select>
        </div>

        <button
          type="button"
          onClick={reset}
          disabled={!isFiltered && !config.showValues}
          className="rounded-lg border border-nn-border px-3 py-1.5 text-xs font-medium text-nn-blue transition-colors hover:bg-nn-blue-light disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-600 dark:text-sky-300 dark:hover:bg-slate-800"
        >
          {t('lab.matrixConfig.reset')}
        </button>
      </div>

      <p className="mt-2 text-[11px] text-nn-gray dark:text-slate-400">
        {isFiltered
          ? t('lab.matrixConfig.filteredSummary', {
              rowType: axisLabel(t, matrixView.rowType),
              colType: axisLabel(t, matrixView.colType),
              rows: rowCount,
              cols: colCount,
            })
          : t('lab.matrixConfig.fullSummary', {
              rowType: axisLabel(t, matrixView.rowType),
              colType: axisLabel(t, matrixView.colType),
              rows: matrixRows.length,
              cols: matrixCols.length,
            })}
      </p>
    </div>
  );
}
