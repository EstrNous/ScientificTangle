import { forwardRef, useImperativeHandle, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { collectSourceRefs } from '../../utils/sourceRefs.js';
import { useSourceRefsPopover } from '../../hooks/useSourceRefsPopover.js';
import { useThemeStore } from '../../stores/themeStore.js';
import { captureElementImage, waitForPaint } from '../../utils/captureElement.js';
import { CollapseIcon, ExpandIcon } from '../admin/AdminIcons.jsx';
import SourceRefsPopover from '../shared/SourceRefsPopover.jsx';

const MAX_SCALE = 12;

function mix(a, b, t) {
  return Math.round(a + (b - a) * t);
}

function cellColors(value, isDark) {
  if (value === 0) {
    return {
      bg: isDark ? '#1e293b' : '#f1f5f9',
      text: isDark ? '#cbd5e1' : '#64748b',
    };
  }

  const t = Math.min(value / MAX_SCALE, 1);

  if (isDark) {
    return {
      bg: `rgb(${mix(30, 0, t)}, ${mix(58, 87, t)}, ${mix(95, 184, t)})`,
      text: t > 0.55 ? '#f8fafc' : '#e2e8f0',
    };
  }

  return {
    bg: `rgb(${mix(232, 0, t)}, ${mix(241, 87, t)}, ${mix(250, 184, t)})`,
    text: t > 0.5 ? '#ffffff' : '#004494',
  };
}

function LegendSwatch({ value, isDark }) {
  const colors = cellColors(value, isDark);
  return (
    <span
      className="inline-block h-3 w-3 rounded-sm border border-black/5 dark:border-white/10"
      style={{ backgroundColor: colors.bg }}
    />
  );
}

function axisLabel(t, type) {
  return t(`lab.nodeTypes.${type}`, { defaultValue: type });
}

const CoverageMatrix = forwardRef(function CoverageMatrix(
  { view, fill = false, showValues = false, expanded = false, onToggleExpand },
  ref,
) {
  const { t } = useTranslation();
  const theme = useThemeStore((s) => s.theme);
  const captureRef = useRef(null);
  const [exporting, setExporting] = useState(false);
  const { popover, openPopover, closePopover } = useSourceRefsPopover();
  const isDark = exporting ? false : theme === 'dark';
  const valuesVisible = exporting || showValues;

  useImperativeHandle(ref, () => ({
    async getExportImage() {
      setExporting(true);
      await waitForPaint();
      const image = await captureElementImage(captureRef.current, { fullContent: true });
      setExporting(false);
      return image;
    },
  }));

  if (!view?.rows?.length || !view?.cols?.length) return null;

  const rowTypeLabel = axisLabel(t, view.rowType);
  const colTypeLabel = axisLabel(t, view.colType);

  const handleCellClick = (event, row, col, value, rowIndex, colIndex) => {
    if (!value) return;
    const cellSources = view.cell_sources ?? view.cellSources;
    const cellItem = cellSources?.[rowIndex]?.[colIndex];
    const sources = collectSourceRefs(cellItem, value);
    if (!sources.length) return;
    openPopover(event, {
      title: t('source.refsTitle'),
      subtitle: t('lab.cellTooltip', { row, col, count: value }),
      sources,
    });
  };

  return (
    <div
      ref={captureRef}
      className={`nn-card bg-white p-4 dark:bg-slate-900 ${fill ? 'flex min-h-0 flex-1 flex-col overflow-hidden' : ''}`}
    >
      <div className="mb-2 flex shrink-0 flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold text-gray-900 dark:text-slate-100">
          {t('lab.matrixTitle', { row: rowTypeLabel, col: colTypeLabel })}
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex flex-wrap gap-2 text-[10px] text-nn-gray dark:text-slate-400">
            <span className="inline-flex items-center gap-1">
              <LegendSwatch value={0} isDark={isDark} /> {t('lab.legend.none')}
            </span>
            <span className="inline-flex items-center gap-1">
              <LegendSwatch value={2} isDark={isDark} /> {t('lab.legend.low')}
            </span>
            <span className="inline-flex items-center gap-1">
              <LegendSwatch value={6} isDark={isDark} /> {t('lab.legend.mid')}
            </span>
            <span className="inline-flex items-center gap-1">
              <LegendSwatch value={12} isDark={isDark} /> {t('lab.legend.high')}
            </span>
          </div>
          {onToggleExpand && (
            <button
              type="button"
              onClick={onToggleExpand}
              className="rounded-md p-1 text-nn-gray transition-colors hover:bg-nn-gray-light hover:text-gray-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100"
              title={expanded ? t('lab.collapseMatrix') : t('lab.expandMatrix')}
              aria-label={expanded ? t('lab.collapseMatrix') : t('lab.expandMatrix')}
            >
              {expanded ? (
                <CollapseIcon className="h-3.5 w-3.5" />
              ) : (
                <ExpandIcon className="h-3.5 w-3.5" />
              )}
            </button>
          )}
        </div>
      </div>
      <p className="mb-2 shrink-0 text-[10px] text-nn-gray dark:text-slate-500">{t('lab.cellClickHint')}</p>
      <div className={`min-h-0 ${fill ? 'flex-1 overflow-auto' : 'overflow-x-auto'}`}>
        <table className="w-full min-w-[480px] border-separate border-spacing-1 text-xs">
          <thead>
            <tr>
              <th className="p-2 text-left font-medium text-nn-gray dark:text-slate-400">
                {rowTypeLabel}
              </th>
              {view.cols.map((col) => (
                <th
                  key={col}
                  className="p-2 text-left font-medium text-gray-900 dark:text-slate-100"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {view.rows.map((row, rowIndex) => (
              <tr key={row}>
                <td className="p-2 font-medium text-gray-900 dark:text-slate-100">{row}</td>
                {view.matrix[rowIndex].map((value, colIndex) => {
                  const colors = cellColors(value, isDark);
                  const col = view.cols[colIndex];
                  const clickable = value > 0;
                  return (
                    <td key={`${row}-${col}`} className="p-0.5">
                      <button
                        type="button"
                        disabled={!clickable}
                        title={
                          clickable
                            ? t('lab.cellTooltip', { row, col, count: value })
                            : t('lab.legend.none')
                        }
                        onClick={(event) => handleCellClick(event, row, col, value, rowIndex, colIndex)}
                        style={{ backgroundColor: colors.bg }}
                        className={`flex h-10 w-full min-w-[2.5rem] items-center justify-center rounded-md ${
                          clickable
                            ? 'cursor-pointer transition-all hover:scale-105 hover:shadow-md hover:ring-2 hover:ring-nn-blue/30'
                            : 'cursor-default'
                        } ${valuesVisible ? '' : 'group'}`}
                      >
                        <span
                          className={`text-sm font-bold tabular-nums ${
                            valuesVisible
                              ? 'opacity-100'
                              : 'opacity-0 transition-opacity duration-150 group-hover:opacity-100'
                          }`}
                          style={{ color: colors.text }}
                        >
                          {value}
                        </span>
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <SourceRefsPopover state={popover} onClose={closePopover} />
    </div>
  );
});

export default CoverageMatrix;
