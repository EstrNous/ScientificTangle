import { apiGet, apiPut, apiOptions } from './client.js';
import { mapApiError } from './errors.js';
import { mapInterestsProfile, serializeInterestsUpdate } from './mappers/productApi.js';

export async function fetchInterestsProfile() {
  try {
    const payload = await apiGet('/interests', apiOptions());
    return mapInterestsProfile(payload);
  } catch (error) {
    throw new Error(mapApiError(error, 'interests_load_failed'));
  }
}

export async function updateInterestsProfile({ rawText, interests }) {
  try {
    const payload = await apiPut('/interests', serializeInterestsUpdate({ rawText, interests }), apiOptions());
    return mapInterestsProfile(payload ?? {});
  } catch (error) {
    throw new Error(mapApiError(error, 'interests_save_failed'));
  }
}

export { mapInterestsProfile, mapInterest } from './mappers/productApi.js';
