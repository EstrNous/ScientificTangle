import { useCallback, useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import PageShell from '../components/shared/PageShell.jsx';
import { ErrorBanner } from '../components/shared/PageState.jsx';
import { UploadAnalysisPanel, UploadDropzone, UploadEntityPanel } from '../components/upload/index.js';
import { ensureAuth } from '../api/auth.js';
import {
  deleteDocument,
  fetchDocument,
  resolveUploadedDocuments,
  uploadFiles,
} from '../api/upload.js';
import { deriveEntitiesFromReport } from '../utils/uploadEntities.js';
import {
  resolveDocumentIdFromState,
  resolveIngestionTaskIdFromState,
  clearNavigationState,
} from '../utils/locationState.js';

const baseURL = import.meta.env.VITE_API_URL || '/api';

function fileKey(entry) {
  return `${entry.kind}:${entry.file.name}`;
}

function uploadedDocumentFromCatalogItem(item) {
  if (!item?.documentId) return null;
  return {
    id: item.documentId,
    filename: item.title || item.sourcePath || item.documentId,
    kind: item.sourceType?.includes('json') ? 'dictionary' : 'document',
  };
}

export default function UploadPage() {
  const { t } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const [files, setFiles] = useState([]);
  const [fileStatuses, setFileStatuses] = useState({});
  const [task, setTask] = useState(null);
  const [uploadedDocuments, setUploadedDocuments] = useState([]);
  const [entities, setEntities] = useState([]);
  const [loading, setLoading] = useState(false);
  const [documentLoading, setDocumentLoading] = useState(false);
  const [deletingDocumentId, setDeletingDocumentId] = useState(null);
  const [error, setError] = useState(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const pollTask = useCallback(async (taskId, token, { isActive = () => true } = {}) => {
    for (let attempt = 0; attempt < 60; attempt += 1) {
      if (!isActive()) return null;
      const response = await fetch(`${baseURL}/tasks/${taskId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!isActive()) return null;
      if (!response.ok) {
        throw new Error('upload_failed');
      }
      const payload = await response.json();
      if (!isActive()) return null;
      setTask(payload);
      if (payload.status === 'completed' || payload.status === 'failed') {
        return payload;
      }
      await new Promise((resolve) => setTimeout(resolve, 1500));
    }
    return null;
  }, []);

  const ingestionTaskId = resolveIngestionTaskIdFromState(location.state);
  const focusedDocumentId = resolveDocumentIdFromState(location.state);

  useEffect(() => {
    if (!ingestionTaskId) return undefined;
    let active = true;
    (async () => {
      try {
        const token = await ensureAuth();
        const payload = await pollTask(ingestionTaskId, token, { isActive: () => active });
        if (!active || !payload) return;
        setTask(payload);
        if (payload.report) {
          setUploadedDocuments(resolveUploadedDocuments(payload.report));
          setEntities(deriveEntitiesFromReport(payload.report));
        }
        clearNavigationState(navigate, location.pathname);
      } catch {
        if (active) setError('upload_failed');
      }
    })();
    return () => {
      active = false;
    };
  }, [ingestionTaskId, location.pathname, navigate, pollTask]);

  useEffect(() => {
    if (!focusedDocumentId || ingestionTaskId) return undefined;
    let active = true;
    (async () => {
      setError(null);
      setDocumentLoading(true);
      try {
        const item = await fetchDocument(focusedDocumentId);
        if (!active) return;
        const document = uploadedDocumentFromCatalogItem(item);
        if (document) {
          setUploadedDocuments([document]);
        }
        clearNavigationState(navigate, location.pathname);
      } catch {
        if (active) setError('document_load_failed');
      } finally {
        if (active) setDocumentLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [focusedDocumentId, ingestionTaskId, location.pathname, navigate]);

  const handleFilesSelected = (selected, kind) => {
    setError(null);
    setTask(null);
    setEntities([]);
    setUploadedDocuments([]);
    const entries = selected.map((file) => ({ file, kind }));
    setFiles((current) => {
      const names = new Set(current.map((entry) => fileKey(entry)));
      const merged = [...current];
      entries.forEach((entry) => {
        if (!names.has(fileKey(entry))) {
          merged.push(entry);
        }
      });
      return merged;
    });
    setFileStatuses((current) => {
      const next = { ...current };
      entries.forEach((entry) => {
        const key = fileKey(entry);
        if (!next[key]) {
          next[key] = 'queued';
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
          delete updated[fileKey(removed)];
          return updated;
        });
      }
      return next;
    });
  };

  const handleDeleteUploadedDocument = async (document) => {
    if (!window.confirm(t('upload.confirmDeleteDocument', { name: document.filename }))) {
      return;
    }
    const snapshot = uploadedDocuments;
    setDeletingDocumentId(document.id);
    setError(null);
    setUploadedDocuments((current) => current.filter((item) => item.id !== document.id));
    try {
      await deleteDocument(document.id);
    } catch (deleteError) {
      setUploadedDocuments(snapshot);
      setError(deleteError?.message ?? 'delete_failed');
    } finally {
      setDeletingDocumentId(null);
    }
  };

  const handleUpload = async () => {
    if (!files.length || loading) return;
    setLoading(true);
    setError(null);
    setEntities([]);
    setUploadedDocuments([]);
    setFileStatuses((current) => {
      const next = { ...current };
      files.forEach((entry) => {
        next[fileKey(entry)] = 'uploading';
      });
      return next;
    });
    try {
      const token = await ensureAuth();
      const groups = { document: [], dictionary: [] };
      files.forEach((entry) => {
        groups[entry.kind].push(entry.file);
      });

      let lastTask = null;
      let lastReport = null;
      const collectedDocuments = [];

      for (const kind of ['document', 'dictionary']) {
        const batch = groups[kind];
        if (!batch.length) continue;
        const payload = await uploadFiles(batch, { kind });
        setTask(payload);
        const completed = await pollTask(payload.id, token, { isActive: () => mountedRef.current });
        lastTask = completed ?? payload;
        if (completed?.status === 'failed') {
          throw new Error('upload_failed');
        }
        if (completed?.report) {
          lastReport = completed.report;
          collectedDocuments.push(...resolveUploadedDocuments(completed.report));
        }
      }

      setTask(lastTask);
      setUploadedDocuments(collectedDocuments);
      setFileStatuses((current) => {
        const next = { ...current };
        files.forEach((entry) => {
          next[fileKey(entry)] = lastTask?.status === 'failed' ? 'failed' : 'completed';
        });
        return next;
      });
      if (lastReport) {
        setEntities(deriveEntitiesFromReport(lastReport));
      }
    } catch (uploadError) {
      setError(uploadError?.message ?? 'upload_failed');
      setFileStatuses((current) => {
        const next = { ...current };
        files.forEach((entry) => {
          next[fileKey(entry)] = 'failed';
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
            <ErrorBanner
              className="mt-3"
              message={t(`upload.errors.${error}`, { defaultValue: error })}
              onRetry={files.length ? handleUpload : undefined}
              retryLabel={t('common.retry')}
            />
          )}
        </div>
        <div className="flex min-h-0 flex-col gap-4">
          <UploadAnalysisPanel
            task={task}
            loading={loading}
            documentLoading={documentLoading}
            uploadedDocuments={uploadedDocuments}
            focusedDocumentId={focusedDocumentId}
            onDeleteDocument={handleDeleteUploadedDocument}
            deletingDocumentId={deletingDocumentId}
          />
          <UploadEntityPanel entities={entities} onChange={setEntities} disabled={loading} />
        </div>
      </div>
    </PageShell>
  );
}
