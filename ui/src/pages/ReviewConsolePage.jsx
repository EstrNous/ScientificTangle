import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import PageShell from '../components/shared/PageShell.jsx';
import Loader from '../components/shared/Loader.jsx';
import {
  CandidateTable,
  ConflictDiffView,
  ReviewActionBar,
  ReviewFilters,
  ReviewSourcePanel,
} from '../components/review/index.js';
import { fetchReviewQueue, submitReviewDecision } from '../api/review.js';
import { fetchSourceDocument, mergeSourceSpan } from '../api/sourceResolver/index.js';
import { useAsyncAction } from '../hooks/useAsyncAction.js';
import conflictsSeed from '../api/mock/conflicts.json';

function mapConflict(item) {
  return {
    id: item.id,
    claimA: item.claim_a ?? item.claimA ?? '',
    claimB: item.claim_b ?? item.claimB ?? '',
    conditionA: item.condition_a ?? item.conditionA ?? '',
    conditionB: item.condition_b ?? item.conditionB ?? '',
    sourceA: item.source_a ?? item.sourceA ?? null,
    sourceB: item.source_b ?? item.sourceB ?? null,
  };
}

function isAccessDeniedError(error) {
  const code = error?.code ?? error?.message ?? '';
  return code === 'access_denied' || String(code).includes('access_denied');
}

export default function ReviewConsolePage() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({ status: 'pending' });
  const [items, setItems] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [source, setSource] = useState(null);
  const [sourceLoading, setSourceLoading] = useState(false);
  const [sourceLocked, setSourceLocked] = useState(false);
  const [sourceId, setSourceId] = useState(null);

  const conflictsById = useMemo(() => {
    const map = new Map();
    conflictsSeed.conflicts.forEach((item) => map.set(item.id, mapConflict(item)));
    return map;
  }, []);

  const loadQueue = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const queue = await fetchReviewQueue(filters);
      setItems(queue.items);
      setSelectedId((current) => {
        if (current && queue.items.some((item) => item.id === current)) {
          return current;
        }
        return queue.items[0]?.id ?? null;
      });
    } catch (loadError) {
      setError(loadError?.message ?? 'review_queue_failed');
      setItems([]);
      setSelectedId(null);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadQueue();
  }, [loadQueue]);

  const selectedCandidate = useMemo(
    () => items.find((item) => item.id === selectedId) ?? null,
    [items, selectedId],
  );

  const selectedConflicts = useMemo(() => {
    if (!selectedCandidate?.conflictIds?.length) return [];
    return selectedCandidate.conflictIds
      .map((id) => conflictsById.get(id))
      .filter(Boolean);
  }, [conflictsById, selectedCandidate]);

  useEffect(() => {
    const spanId = selectedCandidate?.sourceSpanIds?.[0] ?? null;
    if (!spanId) {
      setSource(null);
      setSourceLocked(false);
      setSourceId(null);
      return undefined;
    }

    let cancelled = false;
    setSourceLoading(true);
    setSourceLocked(false);
    setSourceId(spanId);

    fetchSourceDocument(spanId)
      .then((document) => {
        if (cancelled) return;
        if (document?.accessDenied || document?.locked) {
          setSource(null);
          setSourceLocked(true);
          return;
        }
        setSource(mergeSourceSpan(document));
        setSourceLocked(false);
      })
      .catch((loadError) => {
        if (cancelled) return;
        if (isAccessDeniedError(loadError)) {
          setSource(null);
          setSourceLocked(true);
          return;
        }
        setSource(null);
        setSourceLocked(false);
      })
      .finally(() => {
        if (!cancelled) setSourceLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedCandidate]);

  const { execute: decide, loading: deciding, error: decisionError } = useAsyncAction(
    async (decision) => {
      if (!selectedCandidate) return null;
      return submitReviewDecision({
        candidateId: selectedCandidate.id,
        decision,
      });
    },
    {
      onSuccess: () => {
        loadQueue();
      },
    },
  );

  const handleDecision = (decision) => {
    decide(decision, {
      optimistic: () => {
        const snapshot = {
          items: items.map((item) => ({ ...item })),
          selectedId,
        };
        setItems((current) =>
          current.map((item) =>
            item.id === selectedCandidate?.id
              ? { ...item, status: decision, updatedAt: new Date().toISOString() }
              : item,
          ),
        );
        return snapshot;
      },
      rollback: (snapshot) => {
        setItems(snapshot.items);
        setSelectedId(snapshot.selectedId);
      },
    });
  };

  if (loading && !items.length) {
    return <Loader />;
  }

  return (
    <PageShell title={t('review.title')} subtitle={t('review.subtitle')} hideHeading>
      <div className="flex h-full min-h-0 flex-col gap-4">
        <div className="shrink-0">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-slate-100">{t('review.title')}</h2>
          <p className="mt-1 text-sm text-nn-gray dark:text-slate-400">{t('review.subtitle')}</p>
        </div>

        <ReviewFilters filters={filters} onChange={setFilters} />

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200">
            {error}
          </div>
        )}
        {decisionError && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200">
            {t(`review.errors.${decisionError}`, { defaultValue: decisionError })}
          </div>
        )}

        <div className="grid min-h-0 flex-1 gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
          <div className="flex min-h-0 flex-col gap-3">
            <CandidateTable items={items} selectedId={selectedId} onSelect={setSelectedId} />
            <ReviewActionBar
              candidate={selectedCandidate}
              loading={deciding}
              onDecision={handleDecision}
            />
          </div>
          <div className="flex min-h-0 flex-col gap-4">
            <ReviewSourcePanel
              source={source}
              loading={sourceLoading}
              locked={sourceLocked}
              sourceId={sourceId}
            />
            <ConflictDiffView conflicts={selectedConflicts} />
          </div>
        </div>
      </div>
    </PageShell>
  );
}
