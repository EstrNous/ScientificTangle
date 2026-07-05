const DOCUMENT_STAGE_ORDER = ['upload', 'parse', 'extract', 'index', 'complete'];

const STAGE_LABEL_KEYS = {
  upload: 'upload.stages.upload',
  parse: 'upload.stages.parse',
  extract: 'upload.stages.extract',
  index: 'upload.stages.index',
  complete: 'upload.stages.complete',
  dictionary: 'upload.stages.dictionary',
};

function normalizeStageStatus(status) {
  if (status === 'completed' || status === 'done' || status === 'success') return 'done';
  if (status === 'processing' || status === 'active' || status === 'running') return 'active';
  if (status === 'failed' || status === 'error') return 'failed';
  return 'pending';
}

function mapBackendStage(stage, t) {
  const id = stage.id ?? stage.stage ?? stage.name ?? 'unknown';
  return {
    id,
    label: stage.label ?? t(STAGE_LABEL_KEYS[id] ?? id, { defaultValue: id }),
    status: normalizeStageStatus(stage.status),
    warnings: stage.warnings ?? [],
  };
}

function deriveStatusIndex(task) {
  if (!task) return -1;
  if (task.status === 'failed') return DOCUMENT_STAGE_ORDER.indexOf('parse');
  if (task.status === 'pending') return 0;
  if (task.status === 'processing') {
    const report = task.report;
    if (report?.indexed_points_count > 0) return DOCUMENT_STAGE_ORDER.indexOf('index');
    if (report?.extracted_claims_count > 0 || report?.source_spans_count > 0) {
      return DOCUMENT_STAGE_ORDER.indexOf('extract');
    }
    if (report?.documents_count > 0) return DOCUMENT_STAGE_ORDER.indexOf('parse');
    return DOCUMENT_STAGE_ORDER.indexOf('upload');
  }
  if (task.status === 'completed') return DOCUMENT_STAGE_ORDER.length - 1;
  return 0;
}

function deriveDocumentStages(task, t) {
  if (!task) return [];
  const activeIndex = deriveStatusIndex(task);
  const failed = task.status === 'failed';

  return DOCUMENT_STAGE_ORDER.map((id, index) => {
    let status = 'pending';
    if (index < activeIndex) status = 'done';
    else if (index === activeIndex) status = failed ? 'failed' : task.status === 'completed' ? 'done' : 'active';
    else if (task.status === 'completed') status = 'done';

    return {
      id,
      label: t(STAGE_LABEL_KEYS[id], { defaultValue: id }),
      status,
      warnings: index === activeIndex && failed && task.error_message ? [task.error_message] : [],
    };
  });
}

export function resolveUploadTaskStages(task, t) {
  if (!task) return [];
  if (task?.stages?.length) {
    return task.stages.map((stage) => mapBackendStage(stage, t));
  }

  if (task?.task_kind === 'dictionary_ingestion' || task?.report?.stage === 'dictionary') {
    const status = normalizeStageStatus(task.status === 'completed' ? 'done' : task.status);
    return [
      {
        id: 'dictionary',
        label: t(STAGE_LABEL_KEYS.dictionary, { defaultValue: 'dictionary' }),
        status: task.status === 'failed' ? 'failed' : status === 'pending' ? 'active' : status,
        warnings: task.report?.warnings ?? [],
      },
    ];
  }

  return deriveDocumentStages(task, t);
}
