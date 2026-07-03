import CopyButton from '../shared/CopyButton.jsx';
import SourceLink from '../shared/SourceLink.jsx';
import { isSourceColumnName } from '../../utils/sourceColumn.js';

export default function EvidenceTable({ table }) {
  const text = [table.columns.join('\t'), ...table.rows.map((r) => r.join('\t'))].join('\n');
  const sourceColumnIndexes = table.columns
    .map((column, index) => (isSourceColumnName(column) ? index : -1))
    .filter((index) => index >= 0);

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
                    cell
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
