export function buildScientificAnswerFixture(query, fileNames = []) {
  const degraded = /degraded|ограничен/i.test(query ?? '');
  const partial = /partial|частичн/i.test(query ?? '');

  const fileHint =
    fileNames.length > 0
      ? ` Учтены прикреплённые файлы: ${fileNames.join(', ')}.`
      : '';

  if (partial) {
    return {
      short_answer:
        'По доступным фрагментам корпуса нельзя сформировать полный ответ по промышленным режимам.',
      confirmed_observations: [],
      candidate_observations: [
        {
          statement: 'Возможна схема перекачки католита через анодные камеры, но условия не подтверждены.',
          reason_codes: ['unsupported_claim', 'missing_source_span'],
        },
      ],
      limitations: ['Проверены только внутренние отчёты с ограниченным доступом.'],
      conflicts: [],
      gaps: [
        'Нет подтверждённых измерений скорости потока для промышленного масштаба.',
        'Отсутствуют данные по составу электролита за последние 3 года.',
      ],
      follow_up: [
        'Уточните температурный диапазон католита.',
        'Добавьте регламент предприятия в корпус поиска.',
      ],
      degraded_reasons: ['insufficient_accessible_evidence'],
    };
  }

  return {
    short_answer: `По запросу «${query || 'без текста'}» подтверждены режимы циркуляции католита при электроэкстракции никеля.${fileHint}`,
    confirmed_observations: [
      {
        statement: 'Скорость потока католита в лабораторных установках составляет 2–4 м/ч.',
        source_span_ids: ['span-1'],
        claim_ids: ['claim-flow-rate'],
        confidence: 0.88,
      },
      {
        statement: 'Контроль состава электролита выполняется перед подачей в анодные камеры.',
        source_span_ids: ['span-1'],
        claim_ids: ['claim-electrolyte-control'],
        confidence: 0.84,
      },
    ],
    candidate_observations: [
      {
        statement: 'Промышленные установки могут работать при 3–5 м/ч без подтверждённого источника.',
        reason_codes: ['needs_unit_check', 'ambiguous_alias'],
      },
      {
        statement: 'Схема с двойной перекачкой упоминается в смежных процессах.',
        reason_codes: ['unresolved_alias'],
      },
    ],
    limitations: [
      'Данные по составу электролита охватывают только лабораторный масштаб.',
      'География источников ограничена европейскими публикациями.',
    ],
    conflicts: [
      {
        description: 'Скорость потока: 2–4 м/ч в Smith J., 2023 vs 3–5 м/ч во внутреннем отчёте.',
        reason_codes: ['conflicting_values', 'unit_mismatch'],
      },
    ],
    gaps: [
      'Нет данных по промышленным установкам за последние 3 года.',
      'Отсутствуют измерения для условий вне диапазона 15–25 °C.',
    ],
    follow_up: [
      'Уточните диапазон температуры католита.',
      'Добавьте регламент предприятия в корпус.',
      'Сузьте географию поиска до конкретного региона.',
    ],
    degraded_reasons: degraded ? ['insufficient_accessible_evidence', 'access_filtered'] : [],
  };
}
