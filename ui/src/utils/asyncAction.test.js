import { describe, expect, it, vi } from 'vitest';
import { feedbackReducer, createFeedbackState, runAsyncAction } from '../utils/asyncAction.js';

describe('asyncAction utils', () => {
  it('reduces feedback state transitions', () => {
    const initial = createFeedbackState();
    const started = feedbackReducer(initial, { type: 'start' });
    expect(started.loading).toBe(true);
    const succeeded = feedbackReducer(started, { type: 'success', message: 'ok' });
    expect(succeeded.success).toBe('ok');
    const failed = feedbackReducer(succeeded, { type: 'error', message: 'bad' });
    expect(failed.error).toBe('bad');
  });

  it('rolls back on failed runAsyncAction', async () => {
    const rollback = vi.fn();
    await expect(
      runAsyncAction(
        async () => {
          throw new Error('boom');
        },
        {
          optimistic: () => 1,
          rollback,
        },
      ),
    ).rejects.toThrow('boom');
    expect(rollback).toHaveBeenCalledWith(1);
  });
});
