import { useTranslation } from 'react-i18next';
import {
  CHAT_ANSWER_PHASES,
  CHAT_ANSWER_PIPELINE,
  phaseIndex,
  shouldShowAnswerPipeline,
} from '../../utils/chatAnswerLifecycle.js';

function PhaseIcon({ status }) {
  if (status === 'done') {
    return (
      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-nn-blue text-xs text-white">
        ✓
      </span>
    );
  }
  if (status === 'active') {
    return (
      <span className="flex h-5 w-5 shrink-0 items-center justify-center">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-nn-blue border-t-transparent" />
      </span>
    );
  }
  return <span className="h-5 w-5 shrink-0 rounded-full border border-nn-border dark:border-slate-600" />;
}

function phaseStatus(phase, currentPhase) {
  const currentIndex = phaseIndex(currentPhase);
  const stepIndex = phaseIndex(phase);
  if (currentIndex == null || stepIndex == null) {
    return 'pending';
  }
  if (stepIndex < currentIndex) return 'done';
  if (stepIndex === currentIndex) return 'active';
  return 'pending';
}

export default function ChatAnswerStatus({ phase, mode, streamingUxEnabled = false }) {
  const { t } = useTranslation();

  if (phase === CHAT_ANSWER_PHASES.IDLE) return null;

  const showPipeline = shouldShowAnswerPipeline(phase, mode, streamingUxEnabled);

  if (mode === 'session' && !streamingUxEnabled && phase === CHAT_ANSWER_PHASES.PARSING) {
    return (
      <div className="chat-inflight-panel chat-bubble-assistant">
        <p className="flex items-center gap-2 text-sm text-gray-900 dark:text-slate-100">
          <PhaseIcon status="active" />
          {t('chat.lifecycle.sessionWaiting')}
        </p>
      </div>
    );
  }

  if (phase === CHAT_ANSWER_PHASES.ERROR) {
    return (
      <div className="chat-bubble-assistant rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-800 sm:px-4 sm:py-3 dark:border-red-900 dark:bg-red-950 dark:text-red-200">
        {t('chat.lifecycle.error')}
      </div>
    );
  }

  if (phase === CHAT_ANSWER_PHASES.DEGRADED) {
    return (
      <div className="chat-bubble-assistant rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900 sm:px-4 sm:py-2 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-100">
        {t('chat.lifecycle.degraded')}
      </div>
    );
  }

  if (!showPipeline) return null;

  return (
    <div className="chat-inflight-panel chat-bubble-assistant">
      <p className="chat-inflight-title">{t('chat.lifecycle.title')}</p>
      <ul className="space-y-2">
        {CHAT_ANSWER_PIPELINE.map((stepPhase) => {
          const status = phaseStatus(stepPhase, phase);
          return (
            <li
              key={stepPhase}
              className={`flex items-start gap-2 text-sm ${
                status === 'active'
                  ? 'font-medium text-gray-900 dark:text-slate-100'
                  : status === 'done'
                    ? 'text-nn-gray dark:text-slate-400'
                    : 'text-nn-gray/60 dark:text-slate-500'
              }`}
            >
              <PhaseIcon status={status} />
              <span>{t(`chat.lifecycle.phases.${stepPhase}`)}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
