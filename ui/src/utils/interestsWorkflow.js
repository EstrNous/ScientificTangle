import { resolveUseMock } from './runtimeMode.js';
import { fetchInterestsProfile, updateInterestsProfile } from '../api/interests.js';
import { extractInterests } from './interestsExtract.js';
import { loadUserInterests, saveUserInterests } from './interestsStorage.js';

const MODEL_EXTRACTION_WARNINGS = new Set([
  'model_interest_extraction_unavailable',
  'model_interest_extraction_failed',
]);

function applyClientExtractionFallback(profile, rawText) {
  const trimmed = rawText.trim();
  if (!trimmed || (profile.interests?.length ?? 0) > 0) {
    return profile;
  }
  const hasModelWarning = (profile.warnings ?? []).some((item) => MODEL_EXTRACTION_WARNINGS.has(item));
  if (!hasModelWarning) {
    return profile;
  }
  const interests = extractInterests(trimmed);
  if (interests.length === 0) {
    return profile;
  }
  return {
    ...profile,
    interests,
    warnings: [...(profile.warnings ?? []), 'client_interest_extraction_fallback'],
  };
}

export async function loadInterestsProfile(userId) {
  if (resolveUseMock()) {
    return loadUserInterests(userId);
  }
  const profile = await fetchInterestsProfile();
  return applyClientExtractionFallback(
    {
      rawText: profile.rawText,
      interests: profile.interests,
      extractedEntities: profile.extractedEntities ?? [],
      warnings: profile.warnings ?? [],
    },
    profile.rawText ?? '',
  );
}

export async function saveInterestsProfile(userId, rawText) {
  if (resolveUseMock()) {
    const interests = extractInterests(rawText);
    saveUserInterests(userId, rawText, interests);
    return { rawText, interests, extractedEntities: [], warnings: [] };
  }
  const profile = await updateInterestsProfile({ rawText });
  return applyClientExtractionFallback(
    {
      rawText: profile.rawText,
      interests: profile.interests,
      extractedEntities: profile.extractedEntities ?? [],
      warnings: profile.warnings ?? [],
    },
    rawText,
  );
}
