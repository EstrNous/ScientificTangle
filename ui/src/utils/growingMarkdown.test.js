import { describe, expect, it, vi } from 'vitest';
import { revealMarkdownText, splitMarkdownRevealChunks } from './growingMarkdown.js';

describe('growingMarkdown', () => {
  it('splits text into progressive chunks', () => {
    const chunks = splitMarkdownRevealChunks('one two three four five', 8);
    expect(chunks[0]).toBe('one two ');
    expect(chunks[chunks.length - 1]).toBe('one two three four five');
  });

  it('reveals markdown incrementally', async () => {
    const onReveal = vi.fn();
    const result = await revealMarkdownText('alpha beta gamma', {
      onReveal,
      chunkDelayMs: 0,
      chunkSize: 6,
    });
    expect(onReveal.mock.calls.length).toBeGreaterThan(1);
    expect(result).toBe('alpha beta gamma');
  });
});
