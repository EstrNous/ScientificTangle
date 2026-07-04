import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import i18n from '../../i18n/index.js';
import CandidateTable from './CandidateTable.jsx';

const items = [
  {
    id: 'cand-001',
    name: 'NiSO4',
    type: 'substance',
    status: 'pending',
    confidence: 0.82,
    conflictIds: ['conflict-003'],
    sourceSpanIds: ['span-101'],
    updatedAt: '2026-07-04T07:30:00Z',
  },
];

describe('CandidateTable', () => {
  it('renders review statuses and selects rows', () => {
    const onSelect = vi.fn();
    render(
      <I18nextProvider i18n={i18n}>
        <CandidateTable items={items} selectedId="cand-001" onSelect={onSelect} />
      </I18nextProvider>,
    );
    expect(screen.getByText('NiSO4')).toBeInTheDocument();
    expect(screen.getByText(/ожидает|pending/i)).toBeInTheDocument();
    screen.getByText('NiSO4').click();
    expect(onSelect).toHaveBeenCalledWith('cand-001');
  });
});
