import { useTranslation } from 'react-i18next';
import { getEvidenceRowSources } from '../../api/mock/sourceBindings.js';
import { useSourceRefsPopover } from '../../hooks/useSourceRefsPopover.js';
import { isSourceColumnName } from '../../utils/sourceColumn.js';
import CopyButton from '../shared/CopyButton.jsx';
import SourceLink from '../shared/SourceLink.jsx';
import SourceRefsPopover from '../shared/SourceRefsPopover.jsx';

export default function EvidenceTable({ table }) {
  const { t } = useTranslation();
  const { popover, openPopover, closePopover } = useSourceRefsPopover();
  const text = [table.columns.join('\t'), ...table.rows.map((r) => r.join('\t'))].join('\n');
  const sourceColumnIndexes = table.columns
    .map((column, index) => (isSourceColumnName(column) ? index : -1))
    .filter((index) => index >= 0);

  const openRowSources = (event, row, rowIndex) => {
    const sources = getEvidenceRowSources(row, table.columns);
    const label = row.find((cell, index) => !sourceColumnIndexes.includes(index) && cell) ?? row[0];
    openPopover(event, {
      title: t('source.refsTitle'),
      subtitle: t('chat.evidenceRow', { index: rowIndex + 1, label }),
      sources,
    });
  };

  return (
    <div className="overflow-auto">
      <div className="mb-1 flex justify-end">
        <CopyButton text={text} />
      </div>
      <table className="w-full border-collapse text-xs">
        <thead>
          <tr>
            {table.columns.map((c) => (
              <th
                key={c}
                className="border border-nn-border bg-nn-blue-light px-2 py-1 text-left font-semibold text-nn-blue dark:border-slate-600 dark:bg-slate-800"
              >
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row, i) => (
            <tr key={i}>
              {row.map((cell, j) => (
                <td key={j} className="border border-nn-border px-2 py-1 text-gray-900 dark:border-slate-600 dark:text-slate-100">
                  {sourceColumnIndexes.includes(j) ? (
                    <SourceLink sourceRef={cell}>{cell}</SourceLink>
                  ) : (
                    <button
                      type="button"
                      onClick={(event) => openRowSources(event, row, i)}
                      className="w-full rounded px-1 py-0.5 text-left transition-colors hover:bg-nn-blue-light/60 dark:hover:bg-slate-800/60"
                      title={t('chat.evidenceCellHint')}
                    >
                      {cell}
                    </button>
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <SourceRefsPopover state={popover} onClose={closePopover} />
    </div>
  );
}
