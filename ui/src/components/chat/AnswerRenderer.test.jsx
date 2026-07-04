import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '../../test/renderWithProviders.jsx';
import AnswerRenderer from './AnswerRenderer.jsx';
import { buildScientificAnswerFixture } from '../../api/mock/scientificAnswerFixtures.js';

describe('AnswerRenderer', () => {
  it('renders legacy payload without scientific sections', () => {
    const { getByText, queryByText } = renderWithProviders(
      <AnswerRenderer
        message={{
          content: 'Простой legacy ответ',
          confidence: 0.9,
        }}
      />,
    );

    expect(getByText('Простой legacy ответ')).toBeTruthy();
    expect(queryByText('Подтверждённые наблюдения')).toBeNull();
  });

  it('renders scientific answer sections from mock shape', () => {
    const scientific = buildScientificAnswerFixture('никель католит', []);
    const { getByText } = renderWithProviders(
      <AnswerRenderer
        message={{
          content: 'fallback',
          scientific_answer: scientific,
          confidence: 0.82,
          warnings: [{ statement: 'Тестовое предупреждение', reason_codes: ['access_filtered'] }],
        }}
      />,
    );

    expect(getByText('Подтверждённые наблюдения')).toBeTruthy();
    expect(getByText('Кандидаты на проверку')).toBeTruthy();
    expect(getByText('Конфликты в источниках')).toBeTruthy();
    expect(getByText('Пробелы в данных')).toBeTruthy();
    expect(getByText('Следующие шаги')).toBeTruthy();
    expect(getByText('Тестовое предупреждение')).toBeTruthy();
    expect(getByText(scientific.confirmed_observations[0].statement)).toBeTruthy();
  });

  it('shows partial banner when confirmed observations are missing', () => {
    const scientific = {
      short_answer: 'Неполный ответ',
      gaps: ['Нет данных по промышленному масштабу'],
      candidate_observations: [
        { statement: 'Возможный режим без подтверждения', reason_codes: ['unsupported_claim'] },
      ],
    };
    const { getByText } = renderWithProviders(
      <AnswerRenderer
        message={{
          scientific_answer: scientific,
        }}
      />,
    );

    expect(getByText('Ответ неполный — подтверждённых наблюдений недостаточно')).toBeTruthy();
  });
});
