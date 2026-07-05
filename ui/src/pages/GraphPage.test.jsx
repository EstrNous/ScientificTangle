import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../test/renderWithProviders.jsx';
import GraphPage from './GraphPage.jsx';
import { ensureAuth } from '../api/auth.js';
import { fetchGraphData, fetchSearchCatalog } from '../api/graph.js';

vi.mock('../api/auth.js', () => ({
  ensureAuth: vi.fn(() => Promise.resolve()),
}));

vi.mock('../api/graph.js', () => ({
  fetchGraphData: vi.fn(),
  fetchSearchCatalog: vi.fn(),
}));

vi.mock('../components/graph/index.js', () => ({
  GraphSearchPanel: () => null,
  GraphSearchResults: () => null,
  GraphNodeTypeFilters: () => null,
  KnowledgeGraph: () => <div data-testid="graph-canvas" />,
  SyncedEntityTable: () => null,
  VerificationInbox: () => null,
}));

const graphFixture = {
  knowledgeGraph: {
    nodes: [{ id: 'node-ni', label: 'Никель', type: 'Material' }],
    links: [],
  },
  entities: [{ id: 'node-ni', name: 'Никель', type: 'Material', status: 'verified' }],
  candidates: [],
  nodeCombinations: [{ group: 'default', rows: [] }],
};

describe('GraphPage smoke', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchGraphData.mockResolvedValue(graphFixture);
    fetchSearchCatalog.mockResolvedValue({ items: [] });
  });

  it('renders knowledge map after load', async () => {
    renderWithProviders(<GraphPage />);
    await waitFor(() => {
      expect(ensureAuth).toHaveBeenCalled();
      expect(fetchGraphData).toHaveBeenCalled();
      expect(fetchSearchCatalog).toHaveBeenCalled();
    });
    expect(await screen.findByText('1 из 1 узлов · 0 связей')).toBeInTheDocument();
    expect(screen.getByTestId('graph-canvas')).toBeInTheDocument();
  });
});
