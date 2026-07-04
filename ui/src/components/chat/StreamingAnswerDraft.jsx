import { useTranslation } from 'react-i18next';
import { CHAT_ANSWER_PHASES } from '../../utils/chatAnswerLifecycle.js';
import GrowingMarkdown from './GrowingMarkdown.jsx';

const STREAMING_PHASES = new Set([
  CHAT_ANSWER_PHASES.SYNTHESIS,
  CHAT_ANSWER_PHASES.CITATIONS,
]);

export default function StreamingAnswerDraft({ phase, draft, complete }) {
  const { t } = useTranslation();

  if (!draft || !STREAMING_PHASES.has(phase)) return null;

  return (
    <div className="mr-8 rounded-xl border border-nn-border bg-white px-4 py-3 shadow-card dark:border-slate-700 dark:bg-slate-900 dark:shadow-none">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-nn-blue">
        {t('chat.streaming.draftTitle')}
      </p>
      <GrowingMarkdown content={draft} complete={complete} />
    </div>
  );
}
