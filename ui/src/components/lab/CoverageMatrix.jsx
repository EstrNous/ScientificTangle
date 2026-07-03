import { useTranslation } from 'react-i18next';
import { useThemeStore } from '../../stores/themeStore.js';

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

export default function CoverageMatrix({ coverage }) {
  const { t } = useTranslation();
  const theme = useThemeStore((s) => s.theme);
  const isDark = theme === 'dark';

  if (!coverage) return null;

  return (
    <div className="nn-card p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold text-gray-900 dark:text-slate-100">
          {t('lab.coverageTitle')}
        </p>
        <div className="flex flex-wrap gap-3 text-[10px] text-nn-gray dark:text-slate-400">
          <span className="inline-flex items-center gap-1.5">
            <LegendSwatch value={0} isDark={isDark} /> {t('lab.legend.none')}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <LegendSwatch value={2} isDark={isDark} /> {t('lab.legend.low')}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <LegendSwatch value={6} isDark={isDark} /> {t('lab.legend.mid')}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <LegendSwatch value={12} isDark={isDark} /> {t('lab.legend.high')}
          </span>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[480px] border-separate border-spacing-1 text-xs">
          <thead>
            <tr>
              <th className="p-2 text-left font-medium text-nn-gray dark:text-slate-400" />
              {coverage.processes.map((process) => (
                <th
                  key={process}
                  className="p-2 text-left font-medium text-gray-900 dark:text-slate-100"
                >
                  {process}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {coverage.materials.map((material, rowIndex) => (
              <tr key={material}>
                <td className="p-2 font-medium text-gray-900 dark:text-slate-100">{material}</td>
                {coverage.matrix[rowIndex].map((value, colIndex) => {
                  const colors = cellColors(value, isDark);
                  const process = coverage.processes[colIndex];
                  return (
                    <td key={`${material}-${process}`} className="p-0.5">
                      <div
                        title={t('lab.cellTooltip', {
                          material,
                          process,
                          count: value,
                        })}
                        style={{ backgroundColor: colors.bg }}
                        className="group flex h-10 min-w-[2.5rem] cursor-default items-center justify-center rounded-md transition-all hover:scale-105 hover:shadow-md hover:ring-2 hover:ring-nn-blue/30"
                      >
                        <span
                          className="text-sm font-bold tabular-nums opacity-0 transition-opacity duration-150 group-hover:opacity-100"
                          style={{ color: colors.text }}
                        >
                          {value}
                        </span>
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
