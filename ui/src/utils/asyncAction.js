export async function runAsyncAction(action, {
  optimistic,
  rollback,
  onSuccess,
  onError,
} = {}) {
  let snapshot;
  if (optimistic) {
    snapshot = optimistic();
  }
  try {
    const result = await action();
    onSuccess?.(result);
    return result;
  } catch (error) {
    if (rollback && snapshot !== undefined) {
      rollback(snapshot);
    }
    const message = error instanceof Error ? error.message : String(error ?? 'request_failed');
    onError?.(message, error);
    throw error;
  }
}

export function createFeedbackState() {
  return {
    loading: false,
    error: null,
    success: null,
  };
}

export function feedbackReducer(state, action) {
  switch (action.type) {
    case 'start':
      return { loading: true, error: null, success: null };
    case 'success':
      return { loading: false, error: null, success: action.message ?? true };
    case 'error':
      return { loading: false, error: action.message ?? 'request_failed', success: null };
    case 'reset':
      return createFeedbackState();
    default:
      return state;
  }
}
