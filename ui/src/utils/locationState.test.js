import { describe, expect, it, vi } from 'vitest';
import {
  resolveCandidateIdFromState,
  resolveDocumentIdFromState,
  resolveIngestionTaskIdFromState,
  resolveQueryRunIdFromState,
  clearNavigationState,
} from './locationState.js';

describe('locationState', () => {
  it('resolves ingestion task id from canonical and legacy keys', () => {
    expect(resolveIngestionTaskIdFromState({ ingestionTaskId: 'task-1' })).toBe('task-1');
    expect(resolveIngestionTaskIdFromState({ taskId: 'task-2' })).toBe('task-2');
    expect(resolveIngestionTaskIdFromState({ ingestion_task_id: 'task-3' })).toBe('task-3');
    expect(resolveIngestionTaskIdFromState(null)).toBeNull();
  });

  it('resolves document id from camelCase and snake_case', () => {
    expect(resolveDocumentIdFromState({ documentId: 'doc-1' })).toBe('doc-1');
    expect(resolveDocumentIdFromState({ document_id: 'doc-2' })).toBe('doc-2');
  });

  it('resolves query run id from navigation state', () => {
    expect(resolveQueryRunIdFromState({ queryRunId: 'run-1' })).toBe('run-1');
    expect(resolveQueryRunIdFromState({ query_run_id: 'run-2' })).toBe('run-2');
  });

  it('resolves review candidate id from navigation state', () => {
    expect(resolveCandidateIdFromState({ candidateId: 'c-1' })).toBe('c-1');
    expect(resolveCandidateIdFromState({ item_id: 'c-2' })).toBe('c-2');
  });

  it('clears navigation state with replace', () => {
    const navigate = vi.fn();
    clearNavigationState(navigate, '/chat');
    expect(navigate).toHaveBeenCalledWith('/chat', { replace: true, state: null });
  });
});
