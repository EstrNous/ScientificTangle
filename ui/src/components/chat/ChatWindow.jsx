import { useEffect, useRef } from 'react';
import AnswerRenderer from './AnswerRenderer.jsx';
import RetrievalProgress from './RetrievalProgress.jsx';

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

export default function ChatWindow({ messages, retrievalTrace }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, retrievalTrace]);

  return (
    <div className="min-h-0 flex-1 space-y-4 overflow-auto pr-2">
      {messages.length === 0 && !retrievalTrace && (
        <div className="flex h-full items-center justify-center text-sm text-nn-gray dark:text-slate-400">
          Задайте вопрос, чтобы начать диалог
        </div>
      )}
      {messages.map((m) => (
        <div
          key={m.id}
          className={`rounded-xl border px-4 py-3 ${
            m.role === 'user'
              ? 'ml-8 border-nn-blue/20 bg-nn-blue-light dark:bg-slate-800'
              : 'mr-8 border-nn-border bg-white shadow-card dark:border-slate-700 dark:bg-slate-900 dark:shadow-none'
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
      {retrievalTrace && <RetrievalProgress trace={retrievalTrace} />}
      <div ref={bottomRef} />
    </div>
  );
}
