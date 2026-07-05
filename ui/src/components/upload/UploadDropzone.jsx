import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useTranslation } from 'react-i18next';
import { DeleteIcon } from '../admin/AdminIcons.jsx';

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const STATUS_STYLES = {
  queued: 'text-nn-gray dark:text-slate-400',
  uploading: 'text-nn-blue dark:text-sky-400',
  completed: 'text-green-600 dark:text-green-400',
  failed: 'text-red-600 dark:text-red-400',
};

const DOCUMENT_ACCEPT = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'text/plain': ['.txt'],
};

const DICTIONARY_ACCEPT = {
  'application/json': ['.json'],
};

function fileKey(entry) {
  return `${entry.kind}:${entry.file.name}`;
}

export default function UploadDropzone({
  files,
  fileStatuses,
  disabled,
  loading,
  onFilesSelected,
  onUpload,
  onRemoveFile,
}) {
  const { t } = useTranslation();

  const onDrop = useCallback(
    (accepted) => {
      if (!accepted.length || disabled) return;
      const documents = [];
      const dictionaries = [];
      accepted.forEach((file) => {
        if (file.name.toLowerCase().endsWith('.json')) {
          dictionaries.push(file);
        } else {
          documents.push(file);
        }
      });
      if (documents.length) {
        onFilesSelected?.(documents, 'document');
      }
      if (dictionaries.length) {
        onFilesSelected?.(dictionaries, 'dictionary');
      }
    },
    [disabled, onFilesSelected],
  );

  const documentDropzone = useDropzone({
    onDrop,
    disabled: disabled || loading,
    multiple: true,
    noClick: true,
    noKeyboard: true,
    accept: {
      ...DOCUMENT_ACCEPT,
      ...DICTIONARY_ACCEPT,
    },
  });

  const dictionaryDropzone = useDropzone({
    onDrop: (accepted) => {
      if (!accepted.length || disabled) return;
      onFilesSelected?.(accepted, 'dictionary');
    },
    disabled: disabled || loading,
    multiple: true,
    noClick: true,
    noKeyboard: true,
    accept: DICTIONARY_ACCEPT,
  });

  const isDragActive = documentDropzone.isDragActive || dictionaryDropzone.isDragActive;

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      <div
        {...documentDropzone.getRootProps()}
        className={`flex min-h-[280px] flex-1 flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors ${
          isDragActive
            ? 'border-nn-blue bg-nn-blue-light/60 dark:border-sky-500 dark:bg-slate-800'
            : 'border-nn-border bg-nn-gray-light/40 dark:border-slate-600 dark:bg-slate-800/40'
        } ${disabled || loading ? 'pointer-events-none opacity-60' : ''}`}
      >
        <input {...documentDropzone.getInputProps()} />
        <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-white text-nn-blue shadow-card dark:bg-slate-900 dark:text-sky-400">
          <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden>
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
        </div>
        <p className="text-lg font-semibold text-gray-900 dark:text-slate-100">
          {isDragActive ? t('upload.dropActive') : t('upload.dropTitle')}
        </p>
        <p className="mt-2 max-w-md text-sm text-nn-gray dark:text-slate-400">{t('upload.dropHint')}</p>
        <div className="mt-5 flex flex-wrap items-center justify-center gap-3">
          <button
            type="button"
            onClick={documentDropzone.open}
            disabled={disabled || loading}
            className="rounded-lg bg-nn-blue px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-nn-blue-dark disabled:cursor-not-allowed disabled:opacity-50"
          >
            {t('upload.selectFiles')}
          </button>
          <button
            type="button"
            onClick={dictionaryDropzone.open}
            disabled={disabled || loading}
            className="rounded-lg border border-nn-blue bg-white px-5 py-2.5 text-sm font-medium text-nn-blue transition-colors hover:bg-nn-blue-light disabled:cursor-not-allowed disabled:opacity-50 dark:border-sky-500 dark:bg-slate-900 dark:text-sky-400 dark:hover:bg-slate-800"
          >
            {t('upload.selectDictionary')}
          </button>
        </div>
      </div>

      {files.length > 0 && (
        <div className="flex min-h-0 flex-col gap-3">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm font-medium text-gray-900 dark:text-slate-100">
              {t('upload.filesCount', { count: files.length })}
            </p>
            <button
              type="button"
              onClick={onUpload}
              disabled={loading || disabled}
              className="rounded-lg bg-nn-blue px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-nn-blue-dark disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? t('upload.uploading') : t('upload.startUpload')}
            </button>
          </div>
          <ul className="scrollbar-thin scrollbar-thumb-nn-border dark:scrollbar-thumb-slate-600 max-h-48 space-y-2 overflow-y-auto pr-1">
            {files.map((entry, index) => {
              const status = fileStatuses[fileKey(entry)] ?? 'queued';
              return (
                <li
                  key={`${fileKey(entry)}-${index}`}
                  className="flex items-center gap-3 rounded-lg border border-nn-border bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="truncate font-medium text-gray-900 dark:text-slate-100">
                        {entry.file.name}
                      </p>
                      <span className="shrink-0 rounded-full bg-nn-gray-light px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-nn-gray dark:bg-slate-800 dark:text-slate-400">
                        {t(`upload.fileKinds.${entry.kind}`, { defaultValue: entry.kind })}
                      </span>
                    </div>
                    <p className="text-xs text-nn-gray dark:text-slate-400">{formatSize(entry.file.size)}</p>
                  </div>
                  <span className={`shrink-0 text-xs font-medium ${STATUS_STYLES[status] ?? STATUS_STYLES.queued}`}>
                    {t(`upload.fileStatus.${status}`, { defaultValue: status })}
                  </span>
                  {!loading && (
                    <button
                      type="button"
                      onClick={() => onRemoveFile?.(index)}
                      className="inline-flex shrink-0 rounded-md p-1 text-nn-gray transition-colors hover:bg-nn-gray-light hover:text-gray-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100"
                      title={t('upload.removeFile')}
                      aria-label={t('upload.removeFile')}
                    >
                      <DeleteIcon className="h-3.5 w-3.5" />
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
