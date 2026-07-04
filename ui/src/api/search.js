import { apiGet, apiOptions } from './client.js';
import { mapApiError } from './errors.js';

export function buildSearchQuery({
  question = '',
  geo = [],
  sourceTypes = [],
  yearFrom = null,
  yearTo = null,
  numericValue = null,
  numericUnit = '',
  limit = 20,
  offset = 0,
} = {}) {
  const params = new URLSearchParams();
  if (question.trim()) {
    params.set('question', question.trim());
  }
  params.set('limit', String(limit));
  if (offset > 0) {
    params.set('offset', String(offset));
  }
  geo.filter(Boolean).forEach((value) => params.append('geo', value));
  sourceTypes.filter(Boolean).forEach((value) => params.append('source_type', value));
  if (yearFrom != null && yearFrom !== '') {
    params.set('year_from', String(yearFrom));
  }
  if (yearTo != null && yearTo !== '') {
    params.set('year_to', String(yearTo));
  }
  if (numericValue != null && numericValue !== '') {
    params.set('numeric_value', String(numericValue));
  }
  if (numericUnit?.trim()) {
    params.set('numeric_unit', numericUnit.trim());
  }
  return params.toString();
}

export async function searchDocuments(filters = {}) {
  try {
    const query = buildSearchQuery(filters);
    return await apiGet(`/search?${query}`, apiOptions());
  } catch (error) {
    throw new Error(mapApiError(error, 'search_failed'));
  }
}
