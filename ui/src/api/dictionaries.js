import { apiGet, apiPost, apiOptions } from './client.js';
import { mapApiError } from './errors.js';
import { mapDictionaryVersion } from './mappers/productApi.js';

export async function fetchDictionaryVersions() {
  try {
    const payload = await apiGet('/dictionaries', apiOptions());
    const items = Array.isArray(payload) ? payload : payload?.items ?? [];
    return items.map(mapDictionaryVersion);
  } catch (error) {
    throw new Error(mapApiError(error, 'dictionaries_load_failed'));
  }
}

export async function fetchActiveDictionary() {
  try {
    const payload = await apiGet('/dictionaries/active', apiOptions());
    return mapDictionaryVersion(payload);
  } catch (error) {
    throw new Error(mapApiError(error, 'dictionaries_active_failed'));
  }
}

export async function activateDictionaryVersion(versionId) {
  try {
    const payload = await apiPost(
      `/dictionaries/${encodeURIComponent(versionId)}/activate`,
      {},
      apiOptions(),
    );
    return mapDictionaryVersion(payload);
  } catch (error) {
    throw new Error(mapApiError(error, 'dictionary_activate_failed'));
  }
}
