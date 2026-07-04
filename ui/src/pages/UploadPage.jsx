import { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import PageShell from '../components/shared/PageShell.jsx';
import Loader from '../components/shared/Loader.jsx';
import { ensureAuth } from '../api/auth.js';

const baseURL = import.meta.env.VITE_API_URL || '/api';

export default function UploadPage() {
  const { t } = useTranslation();
  const [files, setFiles] = useState([]);
  const [task, setTask] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const pollTask = useCallback(async (taskId, token) => {
    for (let attempt = 0; attempt < 60; attempt += 1) {
      const response = await fetch(`${baseURL}/tasks/${taskId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const payload = await response.json();
      setTask(payload);
      if (payload.status === 'completed' || payload.status === 'failed') {
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, 1500));
    }
  }, []);

  const handleUpload = async () => {
    if (!files.length) return;
    setLoading(true);
    setError(null);
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
      await pollTask(payload.id, token);
    } catch (uploadError) {
      setError(uploadError?.message ?? 'upload_failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageShell>
      <div className="mx-auto flex h-full max-w-2xl flex-col gap-4 p-4">
        <input
          type="file"
          multiple
          onChange={(event) => setFiles(Array.from(event.target.files ?? []))}
          className="text-sm"
        />
        <button type="button" onClick={handleUpload} disabled={loading || !files.length} className="nn-btn-primary w-fit px-4 py-2 text-sm">
          {t('nav.upload')}
        </button>
        {loading && <Loader />}
        {error && <p className="text-sm text-red-600">{error}</p>}
        {task && (
          <div className="nn-card p-4 text-sm">
            <p>status: {task.status}</p>
            {task.report?.documents_count != null && (
              <p>documents: {task.report.documents_count}</p>
            )}
            {task.error_message && <p className="text-red-600">{task.error_message}</p>}
          </div>
        )}
      </div>
    </PageShell>
  );
}
