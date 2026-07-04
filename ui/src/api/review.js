import { apiPost, apiOptions } from './client.js';
import { mapApiError } from './errors.js';
import {
  mapReviewDecisionResult,
  mapReviewQueue,
  serializeReviewDecision,
  serializeReviewQueueRequest,
} from './mappers/productApi.js';

export async function fetchReviewQueue(filters = {}) {
  try {
    const payload = await apiPost('/review/queue', serializeReviewQueueRequest(filters), apiOptions());
    return mapReviewQueue(payload);
  } catch (error) {
    throw new Error(mapApiError(error, 'review_queue_failed'));
  }
}

export async function submitReviewDecision(payload) {
  try {
    const response = await apiPost('/review/decisions', serializeReviewDecision(payload), apiOptions());
    return mapReviewDecisionResult(response);
  } catch (error) {
    throw new Error(mapApiError(error, 'review_decision_failed'));
  }
}

export {
  mapReviewCandidate,
  mapReviewDecisionResult,
  mapReviewQueue,
} from './mappers/productApi.js';
