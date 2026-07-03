import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import SourceLink from './SourceLink.jsx';
import { sourceRefLabel } from '../../api/mock/sourceBindings.js';

export default function SourceRefsPopover({ state, onClose }) {
  const { t } = useTranslation();

  useEffect(() => {
    if (!state) return undefined;
    const onKeyDown = (event) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [state, onClose]);

  if (!state) return null;

  return (
    <>
      <button
        type="button"
        aria-label={t('source.close')}
        className="fixed inset-0 z-40 cursor-default bg-transparent"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        className="fixed z-50 rounded-xl border border-nn-border bg-white p-3 shadow-xl dark:border-slate-600 dark:bg-slate-900"
        style={{
          top: state.position.top,
          left: state.position.left,
          width: state.position.width,
          maxHeight: 'min(70vh, 320px)',
        }}
      >
        <div className="mb-2 border-b border-nn-border pb-2 dark:border-slate-700">
          <p className="text-sm font-semibold text-gray-900 dark:text-slate-100">
            {state.title || t('source.refsTitle')}
          </p>
          {state.subtitle && (
            <p className="mt-0.5 text-[11px] text-nn-gray dark:text-slate-400">{state.subtitle}</p>
          )}
          <p className="mt-1 text-[10px] text-nn-gray dark:text-slate-500">
            {t('source.refsCount', { count: state.sources.length })}
          </p>
        </div>
        <ul className="scrollbar-thin scrollbar-thumb-nn-border dark:scrollbar-thumb-slate-600 max-h-[min(52vh,240px)] space-y-1 overflow-y-auto pr-1">
          {state.sources.map((ref) => (
            <li key={ref}>
              <SourceLink
                sourceRef={ref}
                className="block w-full rounded-md px-2 py-1.5 text-xs hover:bg-nn-blue-light dark:hover:bg-slate-800"
                onOpen={onClose}
              >
                {sourceRefLabel(ref)}
              </SourceLink>
            </li>
          ))}
        </ul>
      </div>
    </>
  );
}
