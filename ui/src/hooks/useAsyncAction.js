import { useCallback, useState } from 'react';

export function useAsyncAction(action, { onSuccess, onError } = {}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const execute = useCallback(
    async (input, { optimistic, rollback } = {}) => {
      setLoading(true);
      setError(null);
      let snapshot;
      if (optimistic) {
        snapshot = optimistic();
      }
      try {
        const result = await action(input);
        onSuccess?.(result, input);
        return result;
      } catch (actionError) {
        if (rollback && snapshot !== undefined) {
          rollback(snapshot);
        }
        const message =
          actionError instanceof Error ? actionError.message : String(actionError ?? 'request_failed');
        setError(message);
        onError?.(message, actionError);
        throw actionError;
      } finally {
        setLoading(false);
      }
    },
    [action, onError, onSuccess],
  );

  return {
    execute,
    loading,
    error,
    clearError,
  };
}
