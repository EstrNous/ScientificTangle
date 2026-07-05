import { useTranslation } from 'react-i18next';
import GraphPanelShell from './GraphPanelShell.jsx';

const STATUS_STYLES = {
  verified: 'bg-nn-blue-light text-nn-blue dark:bg-slate-800 dark:text-sky-300',
  candidate: 'bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300',
  conflicting: 'bg-gray-100 text-gray-700 dark:bg-slate-800 dark:text-slate-300',
};

export default function SyncedEntityTable({
  entities,
  selectedId,
  onSelect,
  expanded,
  onToggleExpand,
  className = '',
}) {
  const { t } = useTranslation();

  return (
    <GraphPanelShell
      title={t('graph.entities')}
      expanded={expanded}
      onToggleExpand={onToggleExpand}
      className={className}
    >
      {!entities?.length ? (
        <p className="text-xs text-nn-gray dark:text-slate-400">{t('graph.emptyFiltered')}</p>
      ) : (
        <div
          className={`scrollbar-thin scrollbar-thumb-nn-border dark:scrollbar-thumb-slate-600 overflow-x-hidden ${
            expanded ? 'h-full overflow-y-auto' : 'max-h-full overflow-y-auto'
          }`}
        >
          <table className="w-full table-fixed border-collapse text-xs">
            <thead className="sticky top-0 z-10 bg-white dark:bg-slate-900">
              <tr className="text-left text-nn-gray dark:text-slate-400">
                <th className="w-[42%] border-b border-nn-border px-2 py-2 font-medium dark:border-slate-600">
                  {t('graph.entityName')}
                </th>
                <th className="w-[33%] border-b border-nn-border px-2 py-2 font-medium dark:border-slate-600">
                  {t('graph.entityType')}
                </th>
                <th className="w-[25%] border-b border-nn-border px-2 py-2 font-medium dark:border-slate-600">
                  {t('graph.entityStatus')}
                </th>
              </tr>
            </thead>
            <tbody>
              {entities.map((entity) => (
                <tr
                  key={entity.id}
                  onClick={() => onSelect?.(entity.id)}
                  className={`cursor-pointer transition-colors ${
                    selectedId === entity.id
                      ? 'bg-nn-blue-light dark:bg-slate-800'
                      : 'hover:bg-nn-gray-light dark:hover:bg-slate-800/60'
                  }`}
                >
                  <td
                    className="border-b border-nn-border px-2 py-2 font-medium text-gray-900 dark:border-slate-700 dark:text-slate-100"
                    title={entity.name}
                  >
                    <span className="block truncate">{entity.name}</span>
                  </td>
                  <td
                    className="border-b border-nn-border px-2 py-2 text-nn-gray dark:border-slate-700 dark:text-slate-400"
                    title={t(`graph.nodeTypes.${entity.type}`, { defaultValue: entity.type })}
                  >
                    <span className="block truncate">
                      {t(`graph.nodeTypes.${entity.type}`, { defaultValue: entity.type })}
                    </span>
                  </td>
                  <td className="border-b border-nn-border px-2 py-2 dark:border-slate-700">
                    <span
                      className={`inline-block max-w-full truncate rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${
                        STATUS_STYLES[entity.status] ?? STATUS_STYLES.candidate
                      }`}
                      title={t(`graph.status.${entity.status}`, { defaultValue: entity.status })}
                    >
                      {t(`graph.status.${entity.status}`, { defaultValue: entity.status })}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </GraphPanelShell>
  );
}
