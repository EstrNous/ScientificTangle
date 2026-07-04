import { apiGet, apiPatch, apiOptions } from './client.js';
import { mapApiError } from './errors.js';
import {
  mapAdminPolicy,
  mapAdminUser,
  serializeAdminPolicyPatch,
  serializeAdminUserPatch,
} from './mappers/productApi.js';

export async function fetchAdminSnapshot() {
  try {
    const payload = await apiGet('/admin', apiOptions());
    return {
      summary: payload.summary ?? {},
      operations: payload.operations ?? {},
      users: (payload.users ?? []).map(mapAdminUser),
      policies: (payload.access_policies ?? payload.policies ?? []).map(mapAdminPolicy),
    };
  } catch (error) {
    throw new Error(mapApiError(error, 'admin_load_failed'));
  }
}

export async function patchAdminUser(userId, patch) {
  try {
    const payload = await apiPatch(
      `/admin/users/${encodeURIComponent(userId)}`,
      serializeAdminUserPatch(patch),
      apiOptions(),
    );
    return mapAdminUser(payload);
  } catch (error) {
    throw new Error(mapApiError(error, 'admin_user_save_failed'));
  }
}

export async function patchAdminPolicy(documentId, accessPolicy) {
  try {
    const payload = await apiPatch(
      `/admin/policies/${encodeURIComponent(documentId)}`,
      serializeAdminPolicyPatch(accessPolicy),
      apiOptions(),
    );
    return mapAdminPolicy(payload);
  } catch (error) {
    throw new Error(mapApiError(error, 'admin_policy_save_failed'));
  }
}

export { mapAdminPolicy, mapAdminUser } from './mappers/productApi.js';
