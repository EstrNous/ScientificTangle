import { describe, expect, it } from 'vitest';
import {
  extractScientificAnswer,
  hasScientificAnswerShape,
  isDegradedScientificAnswer,
  isPartialScientificAnswer,
  normalizeWarnings,
} from './answerPayload.js';

describe('answerPayload', () => {
  it('detects nested scientific_answer shape', () => {
    const message = {
      content: 'legacy',
      scientific_answer: {
        short_answer: 'Краткий ответ',
        confirmed_observations: [{ statement: 'Факт', source_span_ids: ['span-1'] }],
      },
    };

    expect(hasScientificAnswerShape(message)).toBe(true);
    expect(extractScientificAnswer(message)?.short_answer).toBe('Краткий ответ');
  });

  it('falls back to legacy message without scientific fields', () => {
    const message = { content: 'только legacy текст' };
    expect(hasScientificAnswerShape(message)).toBe(false);
    expect(extractScientificAnswer(message)).toBeNull();
  });

  it('detects degraded and partial states', () => {
    const degraded = {
      scientific_answer: {
        short_answer: 'Ответ',
        degraded_reasons: ['insufficient_accessible_evidence'],
      },
    };
    const partial = {
      scientific_answer: {
        gaps: ['Нет данных'],
        candidate_observations: [{ statement: 'Кандидат', reason_codes: ['unsupported_claim'] }],
      },
    };

    const degradedAnswer = extractScientificAnswer(degraded);
    expect(isDegradedScientificAnswer(degradedAnswer, degraded)).toBe(true);
    expect(isPartialScientificAnswer(extractScientificAnswer(partial))).toBe(true);
  });

  it('normalizes warnings with reason codes', () => {
    expect(
      normalizeWarnings([
        'Простое предупреждение',
        { statement: 'С кодом', reason_codes: ['access_filtered'] },
      ]),
    ).toEqual([
      { statement: 'Простое предупреждение', reason_codes: [] },
      { statement: 'С кодом', reason_codes: ['access_filtered'] },
    ]);
  });
});
