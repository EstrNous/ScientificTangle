import { describe, expect, it } from 'vitest';
import { buildReportPayload } from '../utils/reportExport.js';

describe('reportExport', () => {
  it('builds export payload', () => {
    const payload = buildReportPayload('s1', 'Title', [{ role: 'user', content: 'hi' }]);
    expect(payload.sessionId).toBe('s1');
    expect(payload.messages).toHaveLength(1);
    expect(payload.messages[0].content).toBe('hi');
  });

  it('includes assistant metadata in export payload', () => {
    const payload = buildReportPayload('s1', 'Title', [
      {
        role: 'assistant',
        content: 'answer',
        sources: [{ title: 'doc.pdf' }],
        warnings: ['limited evidence'],
      },
    ]);
    expect(payload.messages[0].sources).toHaveLength(1);
    expect(payload.messages[0].warnings).toEqual(['limited evidence']);
  });
});
