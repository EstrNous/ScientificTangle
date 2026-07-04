import { useMock } from '../api/client.js';
import { fetchInterestsProfile, updateInterestsProfile } from '../api/interests.js';
import { extractInterests } from './interestsExtract.js';
import { loadUserInterests, saveUserInterests } from './interestsStorage.js';

export async function loadInterestsProfile(userId) {
  if (useMock) {
    return loadUserInterests(userId);
  }
  const profile = await fetchInterestsProfile();
  return {
    rawText: profile.rawText,
    interests: profile.interests,
    extractedEntities: profile.extractedEntities ?? [],
  };
}

export async function saveInterestsProfile(userId, rawText) {
  if (useMock) {
    const interests = extractInterests(rawText);
    saveUserInterests(userId, rawText, interests);
    return { rawText, interests, extractedEntities: [] };
  }
  const profile = await updateInterestsProfile({ rawText });
  return {
    rawText: profile.rawText,
    interests: profile.interests,
    extractedEntities: profile.extractedEntities ?? [],
  };
}
