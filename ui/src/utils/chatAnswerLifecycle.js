export const CHAT_ANSWER_PHASES = {
  IDLE: 'idle',
  PARSING: 'parsing',
  RETRIEVAL: 'retrieval',
  VERIFICATION: 'verification',
  SYNTHESIS: 'synthesis',
  CITATIONS: 'citations',
  DONE: 'done',
  DEGRADED: 'degraded',
  ERROR: 'error',
};

export const CHAT_ANSWER_PIPELINE = [
  CHAT_ANSWER_PHASES.PARSING,
  CHAT_ANSWER_PHASES.RETRIEVAL,
  CHAT_ANSWER_PHASES.VERIFICATION,
  CHAT_ANSWER_PHASES.SYNTHESIS,
  CHAT_ANSWER_PHASES.CITATIONS,
];

const TERMINAL_PHASES = new Set([
  CHAT_ANSWER_PHASES.DONE,
  CHAT_ANSWER_PHASES.DEGRADED,
  CHAT_ANSWER_PHASES.ERROR,
  CHAT_ANSWER_PHASES.IDLE,
]);

const ALLOWED_TRANSITIONS = {
  [CHAT_ANSWER_PHASES.IDLE]: new Set([
    CHAT_ANSWER_PHASES.PARSING,
    CHAT_ANSWER_PHASES.DONE,
    CHAT_ANSWER_PHASES.DEGRADED,
    CHAT_ANSWER_PHASES.ERROR,
  ]),
  [CHAT_ANSWER_PHASES.PARSING]: new Set([
    CHAT_ANSWER_PHASES.RETRIEVAL,
    CHAT_ANSWER_PHASES.DONE,
    CHAT_ANSWER_PHASES.DEGRADED,
    CHAT_ANSWER_PHASES.ERROR,
  ]),
  [CHAT_ANSWER_PHASES.RETRIEVAL]: new Set([
    CHAT_ANSWER_PHASES.VERIFICATION,
    CHAT_ANSWER_PHASES.DEGRADED,
    CHAT_ANSWER_PHASES.ERROR,
  ]),
  [CHAT_ANSWER_PHASES.VERIFICATION]: new Set([
    CHAT_ANSWER_PHASES.SYNTHESIS,
    CHAT_ANSWER_PHASES.DEGRADED,
    CHAT_ANSWER_PHASES.ERROR,
  ]),
  [CHAT_ANSWER_PHASES.SYNTHESIS]: new Set([
    CHAT_ANSWER_PHASES.CITATIONS,
    CHAT_ANSWER_PHASES.DEGRADED,
    CHAT_ANSWER_PHASES.ERROR,
  ]),
  [CHAT_ANSWER_PHASES.CITATIONS]: new Set([
    CHAT_ANSWER_PHASES.DONE,
    CHAT_ANSWER_PHASES.DEGRADED,
    CHAT_ANSWER_PHASES.ERROR,
  ]),
  [CHAT_ANSWER_PHASES.DONE]: new Set([CHAT_ANSWER_PHASES.IDLE]),
  [CHAT_ANSWER_PHASES.DEGRADED]: new Set([CHAT_ANSWER_PHASES.IDLE]),
  [CHAT_ANSWER_PHASES.ERROR]: new Set([CHAT_ANSWER_PHASES.IDLE]),
};

export function isTerminalPhase(phase) {
  return TERMINAL_PHASES.has(phase);
}

export function canTransitionPhase(from, to) {
  if (from === to) return true;
  const allowed = ALLOWED_TRANSITIONS[from];
  return allowed ? allowed.has(to) : false;
}

export function transitionPhase(current, next) {
  if (!canTransitionPhase(current, next)) {
    return current;
  }
  return next;
}

export function phaseIndex(phase) {
  const index = CHAT_ANSWER_PIPELINE.indexOf(phase);
  return index === -1 ? null : index;
}

export function resolveAnswerPhase(message) {
  if (!message) return CHAT_ANSWER_PHASES.IDLE;
  if (message.lifecycle === CHAT_ANSWER_PHASES.DEGRADED) {
    return CHAT_ANSWER_PHASES.DEGRADED;
  }
  if (message.confidence != null && message.confidence < 0.6) {
    return CHAT_ANSWER_PHASES.DEGRADED;
  }
  return CHAT_ANSWER_PHASES.DONE;
}

export function isSimulatedLifecycleEnabled() {
  return import.meta.env.VITE_CHAT_LIFECYCLE_SIMULATION === 'true';
}
