import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import PageShell from '../components/shared/PageShell.jsx';
import Loader from '../components/shared/Loader.jsx';
import GraphCombinationsTable, { EMPTY_ROW } from '../components/graph/GraphCombinationsTable.jsx';
import {
  GraphSearchPanel,
  GraphSearchResults,
  GraphNodeTypeFilters,
  KnowledgeGraph,
  SyncedEntityTable,
  VerificationInbox,
} from '../components/graph/index.js';
import { ALL_GRAPH_NODE_TYPES } from '../components/graph/graphNodeTypes.js';
import { ensureAuth } from '../api/auth.js';
import { getApiErrorMessage } from '../api/errors.js';
import { fetchGraphData, fetchSearchCatalog } from '../api/graph.js';
import { filterGraphSearchResults } from '../utils/graphSearch.js';
import { filterEntitiesByNodeTypes, filterSubgraphByNodeTypes } from '../utils/graphFilters.js';

const PANELS = {
  ENTITIES: 'entities',
  VERIFICATION: 'verification',
  SEARCH: 'search',
};

export default function GraphPage() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [fullGraph, setFullGraph] = useState(null);
  const [entities, setEntities] = useState([]);
  const [candidates, setCandidates] = useState([]);
  const [combinations, setCombinations] = useState([]);
  const [searchCatalog, setSearchCatalog] = useState([]);
  const [searchResults, setSearchResults] = useState([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [activeNodeTypes, setActiveNodeTypes] = useState(ALL_GRAPH_NODE_TYPES);
  const [graphQuery, setGraphQuery] = useState('');
  const [expandedPanel, setExpandedPanel] = useState(null);
  const [viewMode, setViewMode] = useState('graph');

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setError(null);
      try {
        await ensureAuth();
        const [graphData, searchData] = await Promise.all([fetchGraphData(), fetchSearchCatalog()]);
        if (cancelled) return;
        setFullGraph(graphData.knowledgeGraph ?? graphData.subgraph);
        setEntities(graphData.entities ?? []);
        setCandidates(graphData.candidates ?? []);
        setCombinations(graphData.nodeCombinations ?? []);
        setSearchCatalog(searchData.items ?? []);
        setSelectedNodeId(graphData.entities?.[0]?.id ?? null);
      } catch (loadError) {
        if (!cancelled) {
          setError(getApiErrorMessage(loadError, 'graph_load_failed'));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const filteredSubgraph = useMemo(
    () => filterSubgraphByNodeTypes(fullGraph, activeNodeTypes, graphQuery),
    [fullGraph, activeNodeTypes, graphQuery],
  );

  const filteredEntities = useMemo(
    () => filterEntitiesByNodeTypes(entities, activeNodeTypes, graphQuery),
    [entities, activeNodeTypes, graphQuery],
  );

  useEffect(() => {
    if (!filteredEntities.length) {
      setSelectedNodeId(null);
      return;
    }
    if (!filteredEntities.some((entity) => entity.id === selectedNodeId)) {
      setSelectedNodeId(filteredEntities[0].id);
    }
  }, [filteredEntities, selectedNodeId]);

  const handleSearch = useCallback(
    async (filters) => {
      setGraphQuery(filters.query);
      setIsSearching(true);
      await new Promise((resolve) => setTimeout(resolve, 400));
      const results = filterGraphSearchResults(searchCatalog, filters);
      setSearchResults(results);
      setHasSearched(true);
      setIsSearching(false);
    },
    [searchCatalog],
  );

  const graphStats = useMemo(
    () => ({
      nodes: filteredSubgraph.nodes.length,
      links: filteredSubgraph.links.length,
      total: fullGraph?.nodes?.length ?? 0,
    }),
    [filteredSubgraph, fullGraph],
  );

  const togglePanel = (panel) => {
    setExpandedPanel((prev) => (prev === panel ? null : panel));
  };

  const handleViewModeChange = (mode) => {
    setViewMode(mode);
    if (mode === 'table') setExpandedPanel(null);
  };

  const handleCombinationCellChange = (groupIndex, rowIndex, columnKey, value) => {
    setCombinations((prev) =>
      prev.map((group, gi) =>
        gi !== groupIndex
          ? group
          : {
              ...group,
              rows: (group.rows ?? []).map((row, ri) =>
                ri !== rowIndex ? row : { ...row, [columnKey]: value },
              ),
            },
      ),
    );
  };

  const handleCombinationGroupNameChange = (groupIndex, name) => {
    setCombinations((prev) =>
      prev.map((group, gi) => (gi === groupIndex ? { ...group, group: name } : group)),
    );
  };

  const handleCombinationAddRow = (groupIndex) => {
    setCombinations((prev) =>
      prev.map((group, gi) =>
        gi !== groupIndex
          ? group
          : {
              ...group,
              rows: [...(group.rows ?? []), { ...EMPTY_ROW }],
            },
      ),
    );
  };

  const handleCombinationDeleteRow = (groupIndex, rowIndex) => {
    setCombinations((prev) =>
      prev.map((group, gi) =>
        gi !== groupIndex
          ? group
          : { ...group, rows: (group.rows ?? []).filter((_, ri) => ri !== rowIndex) },
      ),
    );
  };

  const isPanelVisible = (panel) => !expandedPanel || expandedPanel === panel;
  const isPanelExpanded = (panel) => expandedPanel === panel;

  if (loading) return <Loader />;

  if (error) {
    return (
      <PageShell>
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200">
          {t(`graph.errors.${error}`, { defaultValue: error })}
        </div>
      </PageShell>
    );
  }

  return (
    <PageShell>
      <div className="flex h-full min-h-0 flex-col gap-4">
        <GraphSearchPanel onSearch={handleSearch} isSearching={isSearching} />
        <GraphNodeTypeFilters
          activeTypes={activeNodeTypes}
          onChange={setActiveNodeTypes}
          viewMode={viewMode}
          onViewModeChange={handleViewModeChange}
        />

        {viewMode === 'table' ? (
          <GraphCombinationsTable
            groups={combinations}
            activeTypes={activeNodeTypes}
            onCellChange={handleCombinationCellChange}
            onGroupNameChange={handleCombinationGroupNameChange}
            onAddRow={handleCombinationAddRow}
            onDeleteRow={handleCombinationDeleteRow}
          />
        ) : (
          <div className="flex min-h-0 flex-1 gap-4">
            <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-3">
              <div className="flex shrink-0 items-center justify-between gap-2">
                <p className="text-sm font-semibold text-gray-900 dark:text-slate-100">
                  {t('graph.knowledgeMap')}
                </p>
                <p className="text-xs text-nn-gray dark:text-slate-400">
                  {t('graph.statsFiltered', {
                    nodes: graphStats.nodes,
                    links: graphStats.links,
                    total: graphStats.total,
                  })}
                </p>
              </div>
              <div className="min-h-0 flex-1">
                <KnowledgeGraph
                  subgraph={filteredSubgraph}
                  selectedNodeId={selectedNodeId}
                  onNodeClick={setSelectedNodeId}
                  emptyMessage={
                    filteredSubgraph.nodes.length === 0 && fullGraph?.nodes?.length
                      ? t('graph.emptyFiltered')
                      : undefined
                  }
                />
              </div>
            </div>

            <aside className="flex w-96 shrink-0 min-h-0 flex-col gap-3 overflow-hidden">
              {isPanelVisible(PANELS.ENTITIES) && (
                <SyncedEntityTable
                  entities={filteredEntities}
                  selectedId={selectedNodeId}
                  onSelect={setSelectedNodeId}
                  expanded={isPanelExpanded(PANELS.ENTITIES)}
                  onToggleExpand={() => togglePanel(PANELS.ENTITIES)}
                  className={expandedPanel ? 'min-h-0 flex-1' : 'min-h-0 flex-[1.1]'}
                />
              )}
              {isPanelVisible(PANELS.VERIFICATION) && (
                <VerificationInbox
                  candidates={candidates}
                  expanded={isPanelExpanded(PANELS.VERIFICATION)}
                  onToggleExpand={() => togglePanel(PANELS.VERIFICATION)}
                  className={expandedPanel ? 'min-h-0 flex-1' : 'min-h-0 flex-[1.1]'}
                />
              )}
              {isPanelVisible(PANELS.SEARCH) && (
                <GraphSearchResults
                  results={searchResults}
                  hasSearched={hasSearched}
                  expanded={isPanelExpanded(PANELS.SEARCH)}
                  onToggleExpand={() => togglePanel(PANELS.SEARCH)}
                  className={expandedPanel ? 'min-h-0 flex-1' : 'min-h-0 flex-1'}
                />
              )}
            </aside>
          </div>
        )}
      </div>
    </PageShell>
  );
}
