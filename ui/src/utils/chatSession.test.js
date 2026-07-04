import { describe, expect, it } from 'vitest';
import { isEmptyDraftSession, sessionTitleFromText } from './chatSession.js';

describe('sessionTitleFromText', () => {
  it('returns fallback for empty text', () => {
    expect(sessionTitleFromText('   ', 'Новый запрос')).toBe('Новый запрос');
  });

  it('truncates long titles', () => {
    const longText = 'а'.repeat(70);
    expect(sessionTitleFromText(longText, 'Новый запрос')).toBe(`${'а'.repeat(61)}…`);
  });

  it('keeps short titles as-is', () => {
    expect(sessionTitleFromText('Тестовый запрос', 'Новый запрос')).toBe('Тестовый запрос');
  });
});

describe('isEmptyDraftSession', () => {
  const defaultTitle = 'Новый запрос';
  const draft = { id: 's1', title: defaultTitle };

  it('returns true for empty draft with default title', () => {
    expect(isEmptyDraftSession(draft, [], defaultTitle)).toBe(true);
  });

  it('returns false when session is missing', () => {
    expect(isEmptyDraftSession(null, [], defaultTitle)).toBe(false);
  });

  it('returns false when messages exist', () => {
    expect(isEmptyDraftSession(draft, [{ id: 'm1' }], defaultTitle)).toBe(false);
  });

  it('returns false when title was customized', () => {
    expect(
      isEmptyDraftSession({ id: 's1', title: 'Мой запрос' }, [], defaultTitle),
    ).toBe(false);
  });
});
