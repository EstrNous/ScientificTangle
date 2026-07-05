import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import i18n from '../../i18n/index.js';
import ReviewSourcePanel from './ReviewSourcePanel.jsx';

describe('ReviewSourcePanel', () => {
  it('shows locked state for restricted sources', () => {
    render(
      <I18nextProvider i18n={i18n}>
        <ReviewSourcePanel locked sourceId="span-locked" />
      </I18nextProvider>,
    );
    expect(screen.getByText(/Источник недоступен|Source unavailable/)).toBeInTheDocument();
  });

  it('renders table source rows', () => {
    render(
      <I18nextProvider i18n={i18n}>
        <ReviewSourcePanel
          source={{
            id: 'span-205',
            title: 'catholyte_regimes.xlsx',
            tableRowId: 'row-3',
            tableRows: [
              { id: 'row-1', cells: ['Режим', 'Скорость'] },
              { id: 'row-3', cells: ['B', '2–4 м/ч'] },
            ],
          }}
        />
      </I18nextProvider>,
    );
    expect(screen.getByText('2–4 м/ч')).toBeInTheDocument();
    expect(screen.getByText(/row-3/)).toBeInTheDocument();
  });
});
