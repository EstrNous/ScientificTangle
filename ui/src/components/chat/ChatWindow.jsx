import { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import AnswerRenderer from './AnswerRenderer.jsx';
import ChatAnswerStatus from './ChatAnswerStatus.jsx';
import RetrievalProgress from './RetrievalProgress.jsx';
import StreamingAnswerDraft from './StreamingAnswerDraft.jsx';
import { shouldShowRetrievalTrace } from '../../utils/chatAnswerLifecycle.js';

function AttachmentList({ attachments }) {
  if (!attachments?.length) return null;
  return (
    <ul className="mt-2 flex flex-wrap gap-1.5">
      {attachments.map((name) => (
        <li
          key={name}
          className="rounded-full border border-nn-blue/30 bg-white px-2.5 py-0.5 text-xs text-nn-blue dark:bg-slate-800"
        >
          {name}
        </li>
      ))}
    </ul>
  );
}

export default function ChatWindow({
  messages,
  retrievalTrace,
  answerPhase,
  answerMode,
  answerFailReason,
  streamingDraft,
  streamingComplete,
  streamingUxEnabled = false,
}) {
  const { t } = useTranslation();
  const bottomRef = useRef(null);
  const showRetrievalTrace = shouldShowRetrievalTrace(
    retrievalTrace,
    answerPhase,
    answerMode,
    streamingUxEnabled,
  );

  useEffect(() => {
    bottomRef.current?.scrollIntoView?.({ behavior: 'smooth' });
  }, [messages, retrievalTrace, answerPhase, streamingDraft]);

  return (
    <div className="min-h-0 flex-1 space-y-4 overflow-auto pr-2">
      {messages.length === 0 && !retrievalTrace && (
        <div className="flex h-full items-center justify-center px-4 text-center text-sm text-nn-gray dark:text-slate-400">
          {t('chat.emptyPrompt')}
        </div>
      )}
      {messages.map((m) => (
        <div
          key={m.id}
          className={`rounded-xl border px-3 py-2.5 sm:px-4 sm:py-3 ${
            m.role === 'user'
              ? `chat-bubble-user border-nn-blue/20 bg-nn-blue-light dark:bg-slate-800`
              : `chat-bubble-assistant border-nn-border bg-white shadow-card dark:border-slate-700 dark:bg-slate-900 dark:shadow-none`
          }`}
        >
          {m.role === 'assistant' ? (
            <AnswerRenderer message={m} />
          ) : (
            <>
              {m.content && <p className="text-sm text-gray-900 dark:text-slate-100">{m.content}</p>}
              <AttachmentList attachments={m.attachments} />
            </>
          )}
        </div>
      ))}
      <ChatAnswerStatus
        phase={answerPhase}
        mode={answerMode}
        streamingUxEnabled={streamingUxEnabled}
        failReason={answerFailReason}
      />
      {streamingUxEnabled && (
        <StreamingAnswerDraft
          phase={answerPhase}
          draft={streamingDraft}
          complete={streamingComplete}
        />
      )}
      {showRetrievalTrace && <RetrievalProgress trace={retrievalTrace} />}
      <div ref={bottomRef} />
    </div>
  );
}
