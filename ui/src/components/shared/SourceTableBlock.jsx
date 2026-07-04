import { useTranslation } from 'react-i18next';

export default function SourceTableBlock({ rows, highlightedRowId }) {
  const { t } = useTranslation();

  if (!rows?.length) {
    return null;
  }

  const columnCount = Math.max(...rows.map((row) => row.cells?.length ?? 0), 1);

  return (
    <div className="overflow-x-auto rounded-lg border border-nn-border dark:border-slate-600">
      <table className="min-w-full text-left text-sm">
        <tbody>
          {rows.map((row) => {
            const isHighlighted = row.id === highlightedRowId;
            return (
              <tr
                key={row.id}
                className={
                  isHighlighted
                    ? 'bg-amber-50/80 dark:bg-amber-500/10'
                    : 'bg-white dark:bg-slate-950'
                }
              >
                {(row.cells ?? []).map((cell, index) => (
                  <td
                    key={`${row.id}-${index}`}
                    className={`border-b border-nn-border px-3 py-2 text-gray-800 dark:border-slate-700 dark:text-slate-200 ${
                      isHighlighted ? 'font-medium text-amber-950 dark:text-amber-100' : ''
                    }`}
                  >
                    {cell}
                  </td>
                ))}
                {(row.cells?.length ?? 0) < columnCount &&
                  Array.from({ length: columnCount - (row.cells?.length ?? 0) }).map((_, index) => (
                    <td
                      key={`${row.id}-pad-${index}`}
                      className="border-b border-nn-border px-3 py-2 dark:border-slate-700"
                    />
                  ))}
              </tr>
            );
          })}
        </tbody>
      </table>
      {highlightedRowId && (
        <p className="border-t border-nn-border px-3 py-2 text-[11px] text-nn-gray dark:border-slate-700 dark:text-slate-400">
          {t('source.tableRowHighlight', { rowId: highlightedRowId })}
        </p>
      )}
    </div>
  );
}
