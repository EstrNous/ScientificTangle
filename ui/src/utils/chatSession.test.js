import { describe, expect, it } from 'vitest';
import { isEmptyDraftSession, findReusableEmptyDraftSession, sessionTitleFromText } from './chatSession.js';

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

describe('findReusableEmptyDraftSession', () => {
  const defaultTitle = 'Новый запрос';
  const draft = { id: 'draft-1', title: defaultTitle };
  const active = { id: 'active-1', title: 'Запрос A' };

  it('returns active session when it is an empty draft', () => {
    expect(findReusableEmptyDraftSession([draft, active], 'draft-1', [], defaultTitle)).toBe(
      draft,
    );
  });

  it('returns another empty draft when active session has messages', () => {
    expect(
      findReusableEmptyDraftSession([draft, active], 'active-1', [{ id: 'm1' }], defaultTitle),
    ).toBe(draft);
  });

  it('returns null when another draft already has messages', () => {
    const draftWithMessages = { id: 'draft-2', title: defaultTitle };
    expect(
      findReusableEmptyDraftSession(
        [draft, active, draftWithMessages],
        'active-1',
        [{ id: 'm1' }],
        defaultTitle,
        { 'draft-2': [{ id: 'm2' }] },
      ),
    ).toBe(draft);
  });

  it('returns null when no reusable draft exists', () => {
    expect(
      findReusableEmptyDraftSession([active], 'active-1', [{ id: 'm1' }], defaultTitle),
    ).toBeNull();
  });
});
