import { buildScientificAnswerFixture } from './scientificAnswerFixtures.js';
import {
  buildRetrievalSteps,
  buildSimulatedAssistantReply,
} from '../../utils/simulation/answerLifecycleFixtures.js';

export { buildRetrievalSteps };

export function buildMockAssistantReply(query, fileNames) {
  return {
    ...buildSimulatedAssistantReply(query, fileNames),
    scientific_answer: buildScientificAnswerFixture(query, fileNames),
  };
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function runMockChatQuery({ text, files }, { onStep, t, stepDelayMs = 700 }) {
  const fileNames = files.map((f) => f.name);
  const steps = buildRetrievalSteps(fileNames, t);

  for (let i = 0; i < steps.length; i += 1) {
    onStep({
      steps: steps.map((step, index) => ({
        ...step,
        status: index < i ? 'done' : index === i ? 'active' : 'pending',
      })),
      activeStepId: steps[i].id,
    });
    await delay(stepDelayMs);
  }

  onStep({
    steps: steps.map((step) => ({ ...step, status: 'done' })),
    activeStepId: null,
    completed: true,
  });

  await delay(300);
  return buildMockAssistantReply(text, fileNames);
}
