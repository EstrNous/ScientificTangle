import { afterEach, describe, expect, it, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAsyncAction } from '../hooks/useAsyncAction.js';

describe('useAsyncAction', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('runs action and clears loading on success', async () => {
    const action = vi.fn(async (value) => value * 2);
    const { result } = renderHook(() => useAsyncAction(action));
    let output;
    await act(async () => {
      output = await result.current.execute(3);
    });
    expect(output).toBe(6);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('rolls back optimistic state and stores error on failure', async () => {
    const action = vi.fn(async () => {
      throw new Error('save_failed');
    });
    const rollback = vi.fn();
    const { result } = renderHook(() => useAsyncAction(action));
    await act(async () => {
      await expect(
        result.current.execute(null, {
          optimistic: () => 'snapshot',
          rollback,
        }),
      ).rejects.toThrow('save_failed');
    });
    expect(rollback).toHaveBeenCalledWith('snapshot');
    expect(result.current.error).toBe('save_failed');
    expect(result.current.loading).toBe(false);
  });
});
