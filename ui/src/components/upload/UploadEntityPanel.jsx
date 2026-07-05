import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { GRAPH_NODE_TYPES } from '../graph/graphNodeTypes.js';
import { createEmptyEntity } from '../../utils/uploadEntities.js';

function EntityForm({ draft, onChange, onSave, onCancel }) {
  const { t } = useTranslation();

  return (
    <div className="space-y-2 rounded-lg border border-nn-border bg-nn-gray-light/50 p-3 dark:border-slate-600 dark:bg-slate-800/60">
      <input
        value={draft.name}
        onChange={(event) => onChange({ ...draft, name: event.target.value })}
        placeholder={t('upload.entityNamePlaceholder')}
        className="w-full rounded-lg border border-nn-border bg-white px-3 py-2 text-sm outline-none focus:border-nn-blue dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
      />
      <select
        value={draft.type}
        onChange={(event) => onChange({ ...draft, type: event.target.value })}
        className="w-full rounded-lg border border-nn-border bg-white px-3 py-2 text-sm outline-none focus:border-nn-blue dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
      >
        {GRAPH_NODE_TYPES.map((type) => (
          <option key={type} value={type}>
            {t(`graph.nodeTypes.${type}`, { defaultValue: type })}
          </option>
        ))}
      </select>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={onSave}
          disabled={!draft.name.trim()}
          className="rounded-lg bg-nn-blue px-3 py-1.5 text-xs font-medium text-white hover:bg-nn-blue-dark disabled:cursor-not-allowed disabled:opacity-50"
        >
          {t('upload.saveEntity')}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg border border-nn-border bg-white px-3 py-1.5 text-xs font-medium text-nn-gray hover:bg-nn-gray-light dark:border-slate-600 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          {t('upload.cancelEntity')}
        </button>
      </div>
    </div>
  );
}

export default function UploadEntityPanel({ entities, onChange, disabled }) {
  const { t } = useTranslation();
  const [editingId, setEditingId] = useState(null);
  const [draft, setDraft] = useState(null);
  const [adding, setAdding] = useState(false);

  const startEdit = (entity) => {
    setAdding(false);
    setEditingId(entity.id);
    setDraft({ ...entity });
  };

  const startAdd = () => {
    setEditingId(null);
    setAdding(true);
    setDraft(createEmptyEntity());
  };

  const cancelForm = () => {
    setEditingId(null);
    setAdding(false);
    setDraft(null);
  };

  const saveEntity = () => {
    if (!draft?.name.trim()) return;
    const payload = { ...draft, name: draft.name.trim() };
    if (adding) {
      onChange?.([...entities, payload]);
    } else {
      onChange?.(entities.map((entity) => (entity.id === editingId ? payload : entity)));
    }
    cancelForm();
  };

  const removeEntity = (entityId) => {
    onChange?.(entities.filter((entity) => entity.id !== entityId));
    if (editingId === entityId) cancelForm();
  };

  return (
    <section className="nn-card flex min-h-0 flex-1 flex-col p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-slate-100">{t('upload.entitiesTitle')}</h3>
        <button
          type="button"
          onClick={startAdd}
          disabled={disabled || adding || editingId}
          className="rounded-lg border border-nn-border bg-white px-3 py-1.5 text-xs font-medium text-nn-blue hover:bg-nn-blue-light disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-600 dark:bg-slate-900 dark:hover:bg-slate-800"
        >
          {t('upload.addEntity')}
        </button>
      </div>

      {adding && draft && (
        <div className="mb-3">
          <EntityForm draft={draft} onChange={setDraft} onSave={saveEntity} onCancel={cancelForm} />
        </div>
      )}

      {!entities.length && !adding && (
        <p className="text-sm text-nn-gray dark:text-slate-400">{t('upload.entitiesEmpty')}</p>
      )}

      <ul className="scrollbar-thin scrollbar-thumb-nn-border dark:scrollbar-thumb-slate-600 min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
        {entities.map((entity) => (
          <li
            key={entity.id}
            className="rounded-lg border border-nn-border bg-white p-3 dark:border-slate-600 dark:bg-slate-900"
          >
            {editingId === entity.id && draft ? (
              <EntityForm draft={draft} onChange={setDraft} onSave={saveEntity} onCancel={cancelForm} />
            ) : (
              <div className="flex items-start gap-2">
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-gray-900 dark:text-slate-100">{entity.name}</p>
                  <p className="mt-0.5 text-xs text-nn-gray dark:text-slate-400">
                    {t(`graph.nodeTypes.${entity.type}`, { defaultValue: entity.type })}
                    {entity.confidence != null && (
                      <span className="ml-2">
                        {t('graph.confidence')}: {Math.round(entity.confidence * 100)}%
                      </span>
                    )}
                  </p>
                </div>
                <div className="flex shrink-0 gap-1">
                  <button
                    type="button"
                    onClick={() => startEdit(entity)}
                    disabled={disabled || adding}
                    className="rounded-md px-2 py-1 text-xs text-nn-blue hover:bg-nn-blue-light disabled:opacity-50 dark:hover:bg-slate-800"
                  >
                    {t('graph.edit')}
                  </button>
                  <button
                    type="button"
                    onClick={() => removeEntity(entity.id)}
                    disabled={disabled}
                    className="rounded-md px-2 py-1 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50 dark:text-red-400 dark:hover:bg-red-950/40"
                  >
                    {t('upload.deleteEntity')}
                  </button>
                </div>
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
