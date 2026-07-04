import { buildMockAssistantReply, buildRetrievalSteps } from '../api/mock/chatQuery.js';
import { CHAT_ANSWER_PHASES } from './chatAnswerLifecycle.js';
import { revealMarkdownText } from './growingMarkdown.js';

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function runStreamingAnswerLifecycle(
  { text, files },
  {
    onPhaseChange,
    onRetrievalStep,
    onStreamingDraft,
    t,
    phaseDelayMs = 350,
    stepDelayMs = 650,
    chunkDelayMs = 40,
  } = {},
) {
  const fileNames = files.map((file) => file.name);

  onPhaseChange?.(CHAT_ANSWER_PHASES.PARSING);
  await delay(phaseDelayMs);

  onPhaseChange?.(CHAT_ANSWER_PHASES.RETRIEVAL);
  const steps = buildRetrievalSteps(fileNames, t);

  for (let i = 0; i < steps.length; i += 1) {
    onRetrievalStep?.({
      steps: steps.map((step, index) => ({
        ...step,
        status: index < i ? 'done' : index === i ? 'active' : 'pending',
      })),
      activeStepId: steps[i].id,
    });
    await delay(stepDelayMs);
  }

  onRetrievalStep?.({
    steps: steps.map((step) => ({ ...step, status: 'done' })),
    activeStepId: null,
    completed: true,
  });

  onPhaseChange?.(CHAT_ANSWER_PHASES.VERIFICATION);
  await delay(phaseDelayMs);

  onPhaseChange?.(CHAT_ANSWER_PHASES.SYNTHESIS);
  const reply = buildMockAssistantReply(text, fileNames);
  const draftText = reply.content ?? '';

  await revealMarkdownText(draftText, {
    onReveal: (partial) => onStreamingDraft?.(partial, false),
    chunkDelayMs,
  });
  onStreamingDraft?.(draftText, true);

  onPhaseChange?.(CHAT_ANSWER_PHASES.CITATIONS);
  await delay(phaseDelayMs);

  const terminalPhase =
    reply.confidence != null && reply.confidence < 0.6
      ? CHAT_ANSWER_PHASES.DEGRADED
      : CHAT_ANSWER_PHASES.DONE;
  onPhaseChange?.(terminalPhase);

  return { ...reply, lifecycle: terminalPhase };
}
