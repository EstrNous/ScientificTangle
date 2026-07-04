import { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import PageShell from '../components/shared/PageShell.jsx';
import { UploadAnalysisPanel, UploadDropzone, UploadEntityPanel } from '../components/upload/index.js';
import { ensureAuth } from '../api/auth.js';
import { deriveEntitiesFromReport } from '../utils/uploadEntities.js';

const baseURL = import.meta.env.VITE_API_URL || '/api';

export default function UploadPage() {
  const { t } = useTranslation();
  const [files, setFiles] = useState([]);
  const [fileStatuses, setFileStatuses] = useState({});
  const [task, setTask] = useState(null);
  const [entities, setEntities] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const pollTask = useCallback(async (taskId, token) => {
    for (let attempt = 0; attempt < 60; attempt += 1) {
      const response = await fetch(`${baseURL}/tasks/${taskId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error('upload_failed');
      }
      const payload = await response.json();
      setTask(payload);
      if (payload.status === 'completed' || payload.status === 'failed') {
        return payload;
      }
      await new Promise((resolve) => setTimeout(resolve, 1500));
    }
    return null;
  }, []);

  const handleFilesSelected = (selected) => {
    setError(null);
    setTask(null);
    setEntities([]);
    setFiles((current) => {
      const names = new Set(current.map((file) => file.name));
      const merged = [...current];
      selected.forEach((file) => {
        if (!names.has(file.name)) {
          merged.push(file);
        }
      });
      return merged;
    });
    setFileStatuses((current) => {
      const next = { ...current };
      selected.forEach((file) => {
        if (!next[file.name]) {
          next[file.name] = 'queued';
        }
      });
      return next;
    });
  };

  const handleRemoveFile = (index) => {
    setFiles((current) => {
      const removed = current[index];
      const next = current.filter((_, fileIndex) => fileIndex !== index);
      if (removed) {
        setFileStatuses((statuses) => {
          const updated = { ...statuses };
          delete updated[removed.name];
          return updated;
        });
      }
      return next;
    });
  };

  const handleUpload = async () => {
    if (!files.length) return;
    setLoading(true);
    setError(null);
    setEntities([]);
    setFileStatuses((current) => {
      const next = { ...current };
      files.forEach((file) => {
        next[file.name] = 'uploading';
      });
      return next;
    });
    try {
      const token = await ensureAuth();
      const formData = new FormData();
      files.forEach((file) => formData.append('files', file));
      const response = await fetch(`${baseURL}/documents/upload`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (!response.ok) {
        throw new Error('upload_failed');
      }
      const payload = await response.json();
      setTask(payload);
      const completed = await pollTask(payload.id, token);
      setFileStatuses((current) => {
        const next = { ...current };
        files.forEach((file) => {
          next[file.name] = completed?.status === 'failed' ? 'failed' : 'completed';
        });
        return next;
      });
      if (completed?.status === 'completed') {
        setEntities(deriveEntitiesFromReport(completed.report));
      }
    } catch (uploadError) {
      setError(uploadError?.message ?? 'upload_failed');
      setFileStatuses((current) => {
        const next = { ...current };
        files.forEach((file) => {
          next[file.name] = 'failed';
        });
        return next;
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageShell>
      <div className="grid h-full min-h-0 grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="flex min-h-0 flex-col">
          <UploadDropzone
            files={files}
            fileStatuses={fileStatuses}
            disabled={false}
            loading={loading}
            onFilesSelected={handleFilesSelected}
            onUpload={handleUpload}
            onRemoveFile={handleRemoveFile}
          />
          {error && (
            <p className="mt-3 text-sm text-red-600 dark:text-red-400">
              {t(`upload.errors.${error}`, { defaultValue: error })}
            </p>
          )}
        </div>
        <div className="flex min-h-0 flex-col gap-4">
          <UploadAnalysisPanel task={task} loading={loading} />
          <UploadEntityPanel entities={entities} onChange={setEntities} disabled={loading} />
        </div>
      </div>
    </PageShell>
  );
}
