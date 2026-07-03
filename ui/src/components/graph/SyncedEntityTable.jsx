import { useTranslation } from 'react-i18next';

const STATUS_STYLES = {
  verified: 'bg-nn-blue-light text-nn-blue dark:bg-slate-800 dark:text-sky-300',
  candidate: 'bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300',
  conflicting: 'bg-gray-100 text-gray-700 dark:bg-slate-800 dark:text-slate-300',
};

export default function SyncedEntityTable({ entities, selectedId, onSelect }) {
  const { t } = useTranslation();

  return (
    <div className="nn-card flex min-h-0 flex-col p-3">
      <p className="mb-2 shrink-0 text-xs font-semibold uppercase tracking-wide text-nn-gray dark:text-slate-400">
        {t('graph.entities')}
      </p>
      <div className="scrollbar-thin scrollbar-thumb-nn-border dark:scrollbar-thumb-slate-600 overflow-auto">
        <table className="w-full border-collapse text-xs">
          <thead>
            <tr className="text-left text-nn-gray dark:text-slate-400">
              <th className="border-b border-nn-border px-2 py-1.5 font-medium dark:border-slate-600">
                {t('graph.entityName')}
              </th>
              <th className="border-b border-nn-border px-2 py-1.5 font-medium dark:border-slate-600">
                {t('graph.entityType')}
              </th>
              <th className="border-b border-nn-border px-2 py-1.5 font-medium dark:border-slate-600">
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
                <td className="border-b border-nn-border px-2 py-2 font-medium text-gray-900 dark:border-slate-700 dark:text-slate-100">
                  {entity.name}
                </td>
                <td className="border-b border-nn-border px-2 py-2 text-nn-gray dark:border-slate-700 dark:text-slate-400">
                  {t(`graph.nodeTypes.${entity.type}`, { defaultValue: entity.type })}
                </td>
                <td className="border-b border-nn-border px-2 py-2 dark:border-slate-700">
                  <span
                    className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${
                      STATUS_STYLES[entity.status] ?? STATUS_STYLES.candidate
                    }`}
                  >
                    {t(`graph.status.${entity.status}`, { defaultValue: entity.status })}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
