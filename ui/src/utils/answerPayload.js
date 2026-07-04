const SCIENTIFIC_FIELD_KEYS = [
  'short_answer',
  'confirmed_observations',
  'candidate_observations',
  'limitations',
  'conflicts',
  'gaps',
  'follow_up',
  'degraded_reasons',
];

function hasNonEmptyScientificContent(value) {
  if (value == null) return false;
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === 'string') return value.trim().length > 0;
  return true;
}

export function pickScientificFields(source = {}) {
  return SCIENTIFIC_FIELD_KEYS.reduce((result, key) => {
    const value = source[key];
    if (value !== undefined) {
      result[key] = value;
    }
    return result;
  }, {});
}

export function hasScientificAnswerShape(message) {
  if (!message || typeof message !== 'object') return false;

  const nested = message.scientific_answer;
  if (nested && typeof nested === 'object') {
    return SCIENTIFIC_FIELD_KEYS.some((key) => hasNonEmptyScientificContent(nested[key]));
  }

  return SCIENTIFIC_FIELD_KEYS.some((key) => hasNonEmptyScientificContent(message[key]));
}

export function extractScientificAnswer(message) {
  if (!hasScientificAnswerShape(message)) return null;

  if (message.scientific_answer && typeof message.scientific_answer === 'object') {
    return pickScientificFields(message.scientific_answer);
  }

  return pickScientificFields(message);
}

export function isDegradedScientificAnswer(answer, message) {
  if (!answer) return false;
  if (message?.lifecycle === 'degraded') return true;
  if (Array.isArray(answer.degraded_reasons) && answer.degraded_reasons.length > 0) return true;
  if (message?.confidence != null && message.confidence < 0.6) return true;
  return false;
}

export function isPartialScientificAnswer(answer) {
  if (!answer) return false;
  const hasConfirmed = Array.isArray(answer.confirmed_observations) && answer.confirmed_observations.length > 0;
  const hasGaps = Array.isArray(answer.gaps) && answer.gaps.length > 0;
  const hasCandidates =
    Array.isArray(answer.candidate_observations) && answer.candidate_observations.length > 0;
  return !hasConfirmed && (hasGaps || hasCandidates);
}

export function normalizeWarningEntry(entry) {
  if (entry == null) return null;
  if (typeof entry === 'string') {
    return { statement: entry, reason_codes: [] };
  }
  if (typeof entry === 'object') {
    return {
      statement: entry.statement ?? entry.text ?? '',
      reason_codes: Array.isArray(entry.reason_codes) ? entry.reason_codes : [],
    };
  }
  return null;
}

export function normalizeWarnings(warnings) {
  if (!Array.isArray(warnings)) return [];
  return warnings.map(normalizeWarningEntry).filter((item) => item && item.statement);
}
