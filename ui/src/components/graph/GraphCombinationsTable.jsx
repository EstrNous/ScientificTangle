import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { getCombinationRowSources, resolveSourceRef } from '../../api/sourceResolver/index.js';
import { useSourceRefsPopover } from '../../hooks/useSourceRefsPopover.js';
import { isDocumentColumnKey } from '../../utils/sourceColumn.js';
import { DeleteIcon } from '../admin/AdminIcons.jsx';
import SourceLink from '../shared/SourceLink.jsx';
import SourceRefsPopover from '../shared/SourceRefsPopover.jsx';
export const COMBINATION_COLUMNS = [
  { key: 'Regime', type: 'Regime' },
  { key: 'Property', type: 'Property' },
  { key: 'Result', type: 'Result' },
  { key: 'Lab', type: 'Lab' },
  { key: 'Author', type: 'Author' },
  { key: 'Document', type: 'Document' },
];

const EMPTY_ROW = Object.fromEntries(COMBINATION_COLUMNS.map((col) => [col.key, '']));

function rowMatchesTypes(row, activeTypes) {
  return COMBINATION_COLUMNS.some((col) => {
    if (!activeTypes.includes(col.type)) return false;
    const value = row[col.key];
    return value != null && String(value).trim() !== '';
  });
}

const inputClass =
  'w-full min-w-[5rem] rounded border border-transparent bg-transparent px-1.5 py-1 text-center text-xs text-gray-900 outline-none focus:border-nn-blue focus:bg-white dark:text-slate-100 dark:focus:border-sky-500 dark:focus:bg-slate-900';

export default function GraphCombinationsTable({
  groups,
  activeTypes,
  onCellChange,
  onGroupNameChange,
  onAddRow,
  onDeleteRow,
}) {
  const { t } = useTranslation();
  const editable = Boolean(onCellChange);
  const { popover, openPopover, closePopover } = useSourceRefsPopover();

  const openCellSources = (event, row, col, columns) => {
    const sources = getCombinationRowSources(row, columns, isDocumentColumnKey);
    if (!sources.length) return;
    openPopover(event, {
      title: t('source.refsTitle'),
      subtitle: `${col.key}: ${row[col.key] ?? ''}`,
      sources,
    });
  };

  const visibleColumns = useMemo(
    () => COMBINATION_COLUMNS.filter((col) => activeTypes.includes(col.type)),
    [activeTypes],
  );

  const visibleGroups = useMemo(() => {
    if (!groups?.length) return [];
    return groups
      .map((group, groupIndex) => ({
        groupIndex,
        group: group.group,
        rows: (group.rows ?? [])
          .map((row, rowIndex) => ({ row, rowIndex }))
          .filter(({ row }) => rowMatchesTypes(row, activeTypes)),
      }))
      .filter((item) => item.rows.length > 0);
  }, [groups, activeTypes]);

  if (!visibleColumns.length) {
    return (
      <div className="nn-card flex flex-1 items-center justify-center p-6 text-sm text-nn-gray dark:text-slate-400">
        {t('graph.combinationsNoTypes')}
      </div>
    );
  }

  return (
    <div className="nn-card flex min-h-0 flex-1 flex-col overflow-hidden p-4">
      <div className="mb-3 flex shrink-0 flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold text-gray-900 dark:text-slate-100">
          {t('graph.combinationsTitle')}
        </p>
        {editable && (
          <p className="text-[11px] text-nn-gray dark:text-slate-400">
            {t('graph.combinationsEditHint')}
          </p>
        )}
      </div>
      <div className="scrollbar-thin scrollbar-thumb-nn-border dark:scrollbar-thumb-slate-600 min-h-0 flex-1 overflow-auto">
        {visibleGroups.length === 0 ? (
          <p className="text-sm text-nn-gray dark:text-slate-400">{t('graph.combinationsEmpty')}</p>
        ) : (
          <table className="w-full min-w-[720px] border-collapse text-xs">
            <thead>
              <tr className="text-left text-nn-gray dark:text-slate-400">
                {visibleColumns.map((col) => (
                  <th
                    key={col.key}
                    className="border border-nn-border bg-nn-gray-light px-3 py-2 font-medium dark:border-slate-600 dark:bg-slate-800"
                  >
                    {t(`graph.nodeTypes.${col.type}`)}
                  </th>
                ))}
                {editable && onDeleteRow && (
                  <th className="w-10 border border-nn-border bg-nn-gray-light px-2 py-2 dark:border-slate-600 dark:bg-slate-800">
                    <span className="sr-only">{t('graph.combinationsDeleteRow')}</span>
                  </th>
                )}
              </tr>
            </thead>
            <tbody>
              {visibleGroups.map((item) => (
                <GroupRows
                  key={item.groupIndex}
                  item={item}
                  visibleColumns={visibleColumns}
                  editable={editable}
                  onCellChange={onCellChange}
                  onGroupNameChange={onGroupNameChange}
                  onAddRow={onAddRow}
                  onDeleteRow={onDeleteRow}
                  onCellSources={openCellSources}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>
      <SourceRefsPopover state={popover} onClose={closePopover} />
    </div>
  );
}

function GroupRows({
  item,
  visibleColumns,
  editable,
  onCellChange,
  onGroupNameChange,
  onAddRow,
  onDeleteRow,
  onCellSources,
}) {
  const { t } = useTranslation();
  const colSpan = visibleColumns.length + (editable && onDeleteRow ? 1 : 0);

  return (
    <>
      <tr>
        <td
          colSpan={colSpan}
          className="border border-nn-border bg-nn-gray-light px-3 py-2 dark:border-slate-600 dark:bg-slate-800"
        >
          <div className="flex items-center justify-center gap-2">
            {editable && onGroupNameChange ? (
              <input
                value={item.group}
                onChange={(e) => onGroupNameChange(item.groupIndex, e.target.value)}
                className="w-full max-w-md rounded border border-transparent bg-transparent px-2 py-0.5 text-center text-[11px] font-semibold uppercase tracking-wide text-gray-800 outline-none focus:border-nn-blue focus:bg-white dark:text-slate-200 dark:focus:border-sky-500 dark:focus:bg-slate-900"
              />
            ) : (
              <span className="text-center text-[11px] font-semibold uppercase tracking-wide text-gray-800 dark:text-slate-200">
                {item.group}
              </span>
            )}
            {editable && onAddRow && (
              <button
                type="button"
                onClick={() => onAddRow(item.groupIndex)}
                className="shrink-0 rounded-md border border-nn-border px-2 py-0.5 text-[10px] font-medium text-nn-blue hover:bg-nn-blue-light dark:border-slate-600 dark:text-sky-300 dark:hover:bg-slate-700"
              >
                {t('graph.combinationsAddRow')}
              </button>
            )}
          </div>
        </td>
      </tr>
      {item.rows.map(({ row, rowIndex }) => (
        <tr
          key={`${item.groupIndex}-${rowIndex}`}
          className="hover:bg-nn-gray-light/50 dark:hover:bg-slate-800/40"
        >
          {visibleColumns.map((col) => (
            <td
              key={col.key}
              className="border border-nn-border px-1 py-1 text-center dark:border-slate-700"
            >
              {editable && onCellChange ? (
                <DocumentCell
                  columnKey={col.key}
                  value={row[col.key] ?? ''}
                  onChange={(value) => onCellChange(item.groupIndex, rowIndex, col.key, value)}
                />
              ) : (
                <span className="block px-2 py-1.5 text-gray-900 dark:text-slate-100">
                  {isDocumentColumnKey(col.key) ? (
                    <SourceLink sourceRef={row[col.key]}>{row[col.key]}</SourceLink>
                  ) : (
                    <button
                      type="button"
                      onClick={(event) => onCellSources?.(event, row, col, visibleColumns)}
                      className="block w-full rounded px-2 py-1.5 text-gray-900 transition-colors hover:bg-nn-blue-light/60 dark:text-slate-100 dark:hover:bg-slate-800/60"
                      title={t('graph.combinationsCellHint')}
                    >
                      {row[col.key] ?? ''}
                    </button>
                  )}
                </span>
              )}
            </td>
          ))}
          {editable && onDeleteRow && (
            <td className="border border-nn-border px-1 py-1 text-center dark:border-slate-700">
              <button
                type="button"
                onClick={() => onDeleteRow(item.groupIndex, rowIndex)}
                className="inline-flex rounded-md p-1 text-nn-gray transition-colors hover:bg-nn-gray-light hover:text-gray-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100"
                title={t('graph.combinationsDeleteRow')}
                aria-label={t('graph.combinationsDeleteRow')}
              >
                <DeleteIcon className="h-3.5 w-3.5" />
              </button>
            </td>
          )}
        </tr>
      ))}
    </>
  );
}

export { EMPTY_ROW };

function DocumentCell({ columnKey, value, onChange }) {
  const resolved = isDocumentColumnKey(columnKey) ? resolveSourceRef(value) : null;

  return (
    <div className="flex min-w-[5rem] flex-col items-center gap-1">
      <input value={value} onChange={(e) => onChange(e.target.value)} className={inputClass} />
      {resolved ? (
        <SourceLink sourceRef={value} className="text-[10px]">
          {value}
        </SourceLink>
      ) : null}
    </div>
  );
}
