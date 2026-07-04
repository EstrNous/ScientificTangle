import { describe, expect, it, vi } from 'vitest';

vi.mock('../api/client.js', () => ({
  useMock: false,
}));

vi.mock('../api/interests.js', () => ({
  updateInterestsProfile: vi.fn(),
  fetchInterestsProfile: vi.fn(),
}));

describe('interestsWorkflow', () => {
  it('applies client extraction when model service is unavailable', async () => {
    const { updateInterestsProfile } = await import('../api/interests.js');
    updateInterestsProfile.mockResolvedValueOnce({
      rawText: 'электроэкстракция никеля',
      interests: [],
      extractedEntities: {},
      warnings: ['model_interest_extraction_unavailable'],
    });

    const { saveInterestsProfile } = await import('./interestsWorkflow.js');
    const profile = await saveInterestsProfile('user-1', 'электроэкстракция никеля');

    expect(profile.rawText).toBe('электроэкстракция никеля');
    expect(profile.interests.length).toBeGreaterThan(0);
    expect(profile.warnings).toContain('client_interest_extraction_fallback');
  });
});
