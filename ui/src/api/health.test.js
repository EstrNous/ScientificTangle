import { describe, expect, it } from 'vitest';
import { mapHealthPayload } from './health.js';

describe('health api', () => {
  it('maps gateway health/all payload', () => {
    const mapped = mapHealthPayload({
      status: 'degraded',
      peers: [
        { service: 'orchestrator', status: 'ok' },
        { service: 'model', status: 'down', error: 'timeout' },
      ],
    });
    expect(mapped.overall).toBe('degraded');
    expect(mapped.peers).toHaveLength(2);
    expect(mapped.peers[1].status).toBe('down');
  });

  it('defaults missing peer status to down', () => {
    const mapped = mapHealthPayload({ status: 'ok', peers: [{ service: 'gateway' }] });
    expect(mapped.peers[0].status).toBe('down');
  });
});
