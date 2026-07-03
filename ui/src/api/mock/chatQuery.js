export function buildRetrievalSteps(fileNames, t) {
  const files =
    fileNames.length > 0
      ? fileNames
      : ['nickel_report.pdf', 'water_desalination.docx', 'process_handbook_2024.pdf'];

  const steps = [
    { id: 'analyze', label: t('chat.retrieval.analyze') },
    {
      id: 'synonyms',
      label: t('chat.retrieval.synonyms', { terms: 'никель, electrowinning, католит' }),
    },
  ];

  files.forEach((file, index) => {
    steps.push({
      id: `search-${index}`,
      label: t('chat.retrieval.searchFile', {
        file,
        method: t('chat.retrieval.methodHybrid'),
      }),
    });
    steps.push({
      id: `process-${index}`,
      label: t('chat.retrieval.processFile', { file }),
    });
  });

  steps.push(
    { id: 'filter', label: t('chat.retrieval.filterAccess') },
    { id: 'synthesize', label: t('chat.retrieval.synthesize') },
  );

  return steps;
}

export function buildMockAssistantReply(query, fileNames) {
  const fileHint =
    fileNames.length > 0
      ? ` Учтены прикреплённые файлы: ${fileNames.join(', ')}.`
      : ' Поиск выполнен по корпусу внутренних отчётов и регламентов.';

  return {
    id: `m-${Date.now()}`,
    role: 'assistant',
    content: `По запросу «${query || 'без текста'}» найдены релевантные технические решения.${fileHint} В мировой практике применяются схемы с перекачкой католита через анодные камеры с контролем состава электролита.`,
    expanded_synonyms: ['electrowinning', 'электроэкстракция', 'nickel', 'никель', 'католит'],
    confidence: 0.82,
    sources: [
      {
        title: 'Catholyte circulation in nickel electrowinning',
        author: 'Smith J.',
        date: '2023',
        confidence_level: 'verified',
        source_span_id: 'span-1',
      },
      {
        title: fileNames[0] || 'nickel_report.pdf',
        author: 'Внутренний отчёт',
        date: '2024',
        confidence_level: 'internal',
        source_span_id: fileNames[0] === 'water_desalination.docx' ? 'span-2' : 'span-1',
      },
    ],
    evidence_table: {
      columns: ['Параметр', 'Значение', 'Источник'],
      rows: [
        ['Скорость потока', '2–4 м/ч', 'Smith J., 2023'],
        ['Метод поиска', 'BM25 + embeddings', 'Retrieval trace'],
      ],
    },
    retrieval_trace: {
      method: 'hybrid',
      files: fileNames.length > 0 ? fileNames : ['nickel_report.pdf', 'water_desalination.docx'],
      scopes: ['source_spans', 'claims', 'tables'],
    },
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
