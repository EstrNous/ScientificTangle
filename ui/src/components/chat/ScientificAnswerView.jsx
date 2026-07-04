import ReactMarkdown from 'react-markdown';
import { useTranslation } from 'react-i18next';
import { isDegradedScientificAnswer, isPartialScientificAnswer } from '../../utils/answerPayload.js';
import ReasonCodeBadges from './ReasonCodeBadges.jsx';

function AnswerSection({ title, children, tone = 'default' }) {
  const toneClasses = {
    default: 'border-nn-border dark:border-slate-700',
    warning: 'border-amber-300/70 bg-amber-50/50 dark:border-amber-800 dark:bg-amber-950/20',
    muted: 'border-nn-border/70 bg-nn-gray-light/40 dark:border-slate-700 dark:bg-slate-800/40',
    danger: 'border-red-300/70 bg-red-50/50 dark:border-red-900 dark:bg-red-950/20',
  };

  return (
    <section className={`rounded-lg border px-3 py-2 ${toneClasses[tone] ?? toneClasses.default}`}>
      <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-nn-gray dark:text-slate-400">
        {title}
      </h4>
      {children}
    </section>
  );
}

function ObservationList({ items, variant }) {
  if (!items?.length) return null;

  return (
    <ul className="space-y-2">
      {items.map((item, index) => {
        const statement = typeof item === 'string' ? item : item.statement;
        const reasonCodes = typeof item === 'object' ? item.reason_codes : [];
        const confidence = typeof item === 'object' ? item.confidence : null;

        return (
          <li
            key={`${variant}-${index}`}
            className={`text-sm ${
              variant === 'candidate'
                ? 'text-nn-gray dark:text-slate-400'
                : 'text-gray-900 dark:text-slate-100'
            }`}
          >
            <p>{statement}</p>
            {variant === 'confirmed' && confidence != null && (
              <p className="mt-0.5 text-xs text-nn-gray dark:text-slate-500">
                {(confidence * 100).toFixed(0)}%
              </p>
            )}
            {reasonCodes?.length > 0 && <ReasonCodeBadges reasonCodes={reasonCodes} />}
          </li>
        );
      })}
    </ul>
  );
}

function TextList({ items }) {
  if (!items?.length) return null;

  return (
    <ul className="list-disc space-y-1 pl-4 text-sm text-gray-900 dark:text-slate-100">
      {items.map((item, index) => (
        <li key={index}>{typeof item === 'string' ? item : item.description ?? item.statement}</li>
      ))}
    </ul>
  );
}

function ConflictList({ conflicts }) {
  if (!conflicts?.length) return null;

  return (
    <ul className="space-y-2">
      {conflicts.map((conflict, index) => {
        const description =
          typeof conflict === 'string' ? conflict : conflict.description ?? conflict.statement;
        const reasonCodes = typeof conflict === 'object' ? conflict.reason_codes : [];

        return (
          <li key={index} className="text-sm text-gray-900 dark:text-slate-100">
            <p>{description}</p>
            {reasonCodes?.length > 0 && <ReasonCodeBadges reasonCodes={reasonCodes} />}
          </li>
        );
      })}
    </ul>
  );
}

function FollowUpList({ steps }) {
  if (!steps?.length) return null;

  return (
    <ol className="list-decimal space-y-1 pl-4 text-sm text-gray-900 dark:text-slate-100">
      {steps.map((step, index) => (
        <li key={index}>{typeof step === 'string' ? step : step.text ?? step.statement}</li>
      ))}
    </ol>
  );
}

export default function ScientificAnswerView({ answer, message }) {
  const { t } = useTranslation();
  const degraded = isDegradedScientificAnswer(answer, message);
  const partial = isPartialScientificAnswer(answer);

  return (
    <div className="space-y-3 text-sm">
      {(degraded || partial) && (
        <div
          className={`rounded-lg border px-3 py-2 text-xs ${
            degraded
              ? 'border-amber-400/80 bg-amber-50 text-amber-900 dark:border-amber-700 dark:bg-amber-950/30 dark:text-amber-100'
              : 'border-sky-300/80 bg-sky-50 text-sky-900 dark:border-sky-800 dark:bg-sky-950/30 dark:text-sky-100'
          }`}
        >
          <p className="font-medium">
            {degraded ? t('chat.answer.degradedBanner') : t('chat.answer.partialBanner')}
          </p>
          {answer.degraded_reasons?.length > 0 && (
            <ReasonCodeBadges reasonCodes={answer.degraded_reasons} />
          )}
        </div>
      )}

      {answer.short_answer && (
        <div className="prose prose-sm max-w-none dark:prose-invert">
          <ReactMarkdown>{answer.short_answer}</ReactMarkdown>
        </div>
      )}

      {answer.confirmed_observations?.length > 0 && (
        <AnswerSection title={t('chat.answer.confirmedTitle')}>
          <ObservationList items={answer.confirmed_observations} variant="confirmed" />
        </AnswerSection>
      )}

      {answer.candidate_observations?.length > 0 && (
        <AnswerSection title={t('chat.answer.candidateTitle')} tone="muted">
          <p className="mb-2 text-xs text-nn-gray dark:text-slate-500">{t('chat.answer.candidateHint')}</p>
          <ObservationList items={answer.candidate_observations} variant="candidate" />
        </AnswerSection>
      )}

      {answer.limitations?.length > 0 && (
        <AnswerSection title={t('chat.answer.limitationsTitle')} tone="warning">
          <TextList items={answer.limitations} />
        </AnswerSection>
      )}

      {answer.conflicts?.length > 0 && (
        <AnswerSection title={t('chat.answer.conflictsTitle')} tone="danger">
          <ConflictList conflicts={answer.conflicts} />
        </AnswerSection>
      )}

      {answer.gaps?.length > 0 && (
        <AnswerSection title={t('chat.answer.gapsTitle')} tone="warning">
          <TextList items={answer.gaps} />
        </AnswerSection>
      )}

      {answer.follow_up?.length > 0 && (
        <AnswerSection title={t('chat.answer.followUpTitle')}>
          <FollowUpList steps={answer.follow_up} />
        </AnswerSection>
      )}
    </div>
  );
}
