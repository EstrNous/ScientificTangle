import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../test/renderWithProviders.jsx';
import StrategicCoveragePage from './StrategicCoveragePage.jsx';
import { ensureAuth } from '../api/auth.js';
import { fetchStrategicMetrics } from '../api/strategic.js';

vi.mock('../api/auth.js', () => ({
  ensureAuth: vi.fn(() => Promise.resolve()),
}));

vi.mock('../api/strategic.js', () => ({
  fetchStrategicMetrics: vi.fn(),
}));

const metricsFixture = {
  updated_at: '2026-01-01T00:00:00Z',
  directions: [{ id: 'hydro', name: 'Гидрометаллургия', coverage: 0.7, documents: 5 }],
  totals: {
    documents: 5,
    claims: 15,
    verified_claims: 10,
    candidates: 3,
    gaps: 1,
    conflicts: 0,
  },
  low_coverage_topics: [],
  high_conflict_topics: [],
};

describe('StrategicCoveragePage smoke', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchStrategicMetrics.mockResolvedValue(metricsFixture);
  });

  it('renders coverage dashboard after load', async () => {
    renderWithProviders(<StrategicCoveragePage />);
    await waitFor(() => {
      expect(ensureAuth).toHaveBeenCalled();
      expect(fetchStrategicMetrics).toHaveBeenCalled();
    });
    expect(await screen.findByText('Покрытие базы знаний')).toBeInTheDocument();
    expect(screen.getByText('Покрытие')).toBeInTheDocument();
  });
});
