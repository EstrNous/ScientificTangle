import { useRef, useState } from 'react';

const ACCEPT = '.pdf,.doc,.docx,.txt,.md,.xlsx,.csv';

function PaperclipIcon() {
  return (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.75}
        d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
      />
    </svg>
  );
}

export default function ChatInput({ onSend }) {
  const fileRef = useRef(null);
  const [files, setFiles] = useState([]);

  const addFiles = (incoming) => {
    if (!incoming?.length) return;
    setFiles((prev) => {
      const names = new Set(prev.map((f) => f.name));
      return [...prev, ...incoming.filter((f) => !names.has(f.name))];
    });
  };

  const removeFile = (name) => {
    setFiles((prev) => prev.filter((f) => f.name !== name));
  };

  const resetForm = (form) => {
    form.reset();
    setFiles([]);
    if (fileRef.current) fileRef.current.value = '';
  };

  return (
    <form
      className="flex shrink-0 flex-col gap-2 border-t border-nn-border pt-4 dark:border-slate-700"
      onSubmit={(e) => {
        e.preventDefault();
        const fd = new FormData(e.currentTarget);
        const text = String(fd.get('message') ?? '').trim();
        if (!text && files.length === 0) return;
        onSend?.({ text, files: [...files] });
        resetForm(e.currentTarget);
      }}
    >
      {files.length > 0 && (
        <ul className="flex flex-wrap gap-2">
          {files.map((file) => (
            <li
              key={file.name}
              className="flex items-center gap-1.5 rounded-full border border-nn-blue/30 bg-nn-blue-light px-3 py-1 text-xs text-nn-blue dark:bg-slate-800"
            >
              <PaperclipIcon />
              <span className="max-w-[12rem] truncate">{file.name}</span>
              <button
                type="button"
                onClick={() => removeFile(file.name)}
                className="ml-0.5 text-nn-blue hover:text-nn-blue-dark"
                aria-label={`Убрать ${file.name}`}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="flex gap-2">
        <input
          ref={fileRef}
          type="file"
          multiple
          accept={ACCEPT}
          className="hidden"
          onChange={(e) => {
            addFiles(Array.from(e.target.files ?? []));
            e.target.value = '';
          }}
        />
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          className="flex shrink-0 items-center justify-center rounded-lg border border-nn-border px-3 text-nn-blue transition-colors hover:border-nn-blue hover:bg-nn-blue-light dark:border-slate-600 dark:hover:bg-slate-800"
          aria-label="Прикрепить файл"
          title="Прикрепить PDF, DOCX, TXT"
        >
          <PaperclipIcon />
        </button>
        <input
          name="message"
          className="min-w-0 flex-1 rounded-lg border border-nn-border bg-nn-gray-light px-4 py-2.5 text-sm text-gray-900 outline-none focus:border-nn-blue focus:ring-1 focus:ring-nn-blue dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
          placeholder="Задайте вопрос…"
        />
        <button type="submit" className="nn-btn-ghost shrink-0">
          Отправить
          <span aria-hidden>›</span>
        </button>
      </div>
    </form>
  );
}
