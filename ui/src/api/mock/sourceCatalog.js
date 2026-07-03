const SOURCE_ENTRIES = {
  'span-1': {
    id: 'span-1',
    title: 'nickel_report.pdf',
    file_name: 'nickel_report.pdf',
    mime_type: 'application/pdf',
    page: 12,
    total_pages: 48,
    section: 'Циркуляция католита',
    highlight: 'скорость потока католита составляет 2–4 м/ч',
    aliases: [
      'Smith J., 2023',
      'Smith J.',
      'Catholyte circulation in nickel electrowinning',
      'nickel_report',
    ],
    pages: {
      11: {
        raw_text:
          'Глава 4. Гидродинамика электролитных ячеек. Перед выбором режима циркуляции оценивают геометрию анодных камер и допустимый перепад давления на мембране.',
      },
      12: {
        raw_text:
          'Оптимальная скорость потока католита составляет 2–4 м/ч при температуре электролита 55–60 °C. При более низкой скорости возрастает риск локального перенасыщения ионами металла.',
        highlight: 'скорость потока католита составляет 2–4 м/ч',
      },
      13: {
        raw_text:
          'Контроль температуры поддерживается теплообменниками на линии оборота. Отклонение более чем на 5 °C от уставки требует корректировки тока выпрямителя.',
      },
    },
  },
  'span-2': {
    id: 'span-2',
    title: 'water_desalination.docx',
    file_name: 'water_desalination.docx',
    mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    page: 4,
    total_pages: 22,
    section: 'Обессоливание',
    highlight: 'сухом остатке исходной воды 1200 мг/дм³',
    aliases: ['Обзор отечественной практики, 2022'],
    pages: {
      3: {
        raw_text:
          'Для шахтных вод с повышенной минерализацией рассматривают схемы с предварительным осветлением и мембранной доочисткой.',
      },
      4: {
        raw_text:
          'При сухом остатке исходной воды 1200 мг/дм³ схема с обратным осмосом обеспечивает выход ≤ 800 мг/дм³. Режим промывки мембран задаётся по проводимости фильтрата.',
        highlight: 'сухом остатке исходной воды 1200 мг/дм³',
      },
      5: {
        raw_text:
          'Экономическая эффективность схемы зависит от стоимости реагентов коагуляции и частоты замены мембранных модулей.',
      },
    },
  },
  'span-3': {
    id: 'span-3',
    title: 'J. Hydrometallurgy, 2024',
    file_name: 'hydrometallurgy_2024.pdf',
    mime_type: 'application/pdf',
    page: 7,
    total_pages: 14,
    section: 'Электролиз никеля',
    highlight: 'плотность тока 180–220 А/м²',
    aliases: ['J. Hydrometallurgy, 2024'],
    pages: {
      6: {
        raw_text:
          'В промышленных установках электроэкстракции никеля ключевым параметром остаётся состав электролита и стабильность pH в катодной зоне.',
      },
      7: {
        raw_text:
          'Рекомендуемый диапазон плотности тока 180–220 А/м² при активной циркуляции католита. Превышение верхней границы увеличивает долю побочных реакций.',
        highlight: 'плотность тока 180–220 А/м²',
      },
      8: {
        raw_text:
          'Авторы отмечают чувствительность процесса к содержанию примесей железа и кобальта в растворе.',
      },
    },
  },
  'span-4': {
    id: 'span-4',
    title: 'Внутренний отчёт, 2024',
    file_name: 'internal_report_2024.pdf',
    mime_type: 'application/pdf',
    page: 3,
    total_pages: 18,
    section: 'Сравнение режимов',
    highlight: 'циркуляцию католита 1,5–2,5 м/ч',
    aliases: ['Внутренний отчёт, 2024', 'Внутренний отчёт'],
    pages: {
      2: {
        raw_text:
          'Отчёт подготовлен по результатам пилотных испытаний на установке №2. Сравнивались режимы с постоянной и переменной скоростью потока.',
      },
      3: {
        raw_text:
          'Для текущей конфигурации ячеек предпочтительна циркуляцию католита 1,5–2,5 м/ч при стабильной температуре 58 °C. Отклонение от диапазона снижает токовую эффективность.',
        highlight: 'циркуляцию католита 1,5–2,5 м/ч',
      },
      4: {
        raw_text:
          'Рекомендуется еженедельный контроль содержания хлоридов и сульфатов в оборотном растворе.',
      },
    },
  },
  'span-5': {
    id: 'span-5',
    title: 'Протокол плавки №14',
    file_name: 'melt_protocol_14.pdf',
    mime_type: 'application/pdf',
    page: 2,
    total_pages: 6,
    section: 'Температурный режим',
    highlight: 'температуру плавки 1650–1680 °C',
    aliases: ['Протокол плавки №14'],
    pages: {
      1: {
        raw_text:
          'Протокол испытаний плавки №14. Цель — подтвердить воспроизводимость режима для сплава VT6.',
      },
      2: {
        raw_text:
          'Операторы удерживали температуру плавки 1650–1680 °C в течение 40 минут до начала разливки. Отклонения фиксировались в журнале печи.',
        highlight: 'температуру плавки 1650–1680 °C',
      },
      3: {
        raw_text:
          'После разливки выполнен отбор проб для химического анализа и механических испытаний.',
      },
    },
  },
  'span-6': {
    id: 'span-6',
    title: 'Материалы конференции, 2023',
    file_name: 'conference_2023.pdf',
    mime_type: 'application/pdf',
    page: 5,
    total_pages: 12,
    section: 'Практика цехов',
    highlight: 'скорости потока 3,2 м/ч',
    aliases: ['Материалы конференции, 2023'],
    pages: {
      4: {
        raw_text:
          'Доклад описывает опыт модернизации линии электролиза на одном из предприятий отрасли.',
      },
      5: {
        raw_text:
          'На действующей линии достигнута устойчивая работа при скорости потока 3,2 м/ч без роста шлама на катоде. Авторы связывают эффект с обновлённой геометрией перегородок.',
        highlight: 'скорости потока 3,2 м/ч',
      },
      6: {
        raw_text:
          'Предложена методика оперативного контроля по проводимости и мутности электролита.',
      },
    },
  },
  'span-7': {
    id: 'span-7',
    title: 'process_handbook_2024.pdf',
    file_name: 'process_handbook_2024.pdf',
    mime_type: 'application/pdf',
    page: 31,
    total_pages: 120,
    section: 'Гидрометаллургия',
    highlight: 'гибридный поиск BM25 и embeddings',
    aliases: ['process_handbook_2024.pdf', 'Retrieval trace'],
    pages: {
      30: {
        raw_text:
          'Справочник описывает типовые схемы подготовки растворов и требования к качеству исходного сырья.',
      },
      31: {
        raw_text:
          'Для извлечения фрагментов из корпуса документов применяется гибридный поиск BM25 и embeddings с последующей фильтрацией по уровню доступа.',
        highlight: 'гибридный поиск BM25 и embeddings',
      },
      32: {
        raw_text:
          'Результаты ранжируются по релевантности и подтверждаются ссылкой на исходный фрагмент.',
      },
    },
  },
  'span-8': {
    id: 'span-8',
    title: 'confidential_process_2024.pdf',
    file_name: 'confidential_process_2024.pdf',
    mime_type: 'application/pdf',
    page: 6,
    total_pages: 12,
    section: 'Режимы электролиза',
    highlight: 'конфиденциальный регламент процесса',
    aliases: ['confidential_process_2024.pdf'],
    pages: {
      5: {
        raw_text:
          'Документ содержит ограниченную информацию о параметрах промышленной установки. Распространение вне утверждённого перечня ролей запрещено.',
      },
      6: {
        raw_text:
          'Действующий конфиденциальный регламент процесса определяет допустимые отклонения по току, температуре и составу электролита для линии №3.',
        highlight: 'конфиденциальный регламент процесса',
      },
      7: {
        raw_text:
          'Изменения режима допускаются только после согласования с технологом и фиксации в журнале смены.',
      },
    },
  },
  'span-9': {
    id: 'span-9',
    title: 'pilot_hl_nickel.zip',
    file_name: 'pilot_hl_nickel.zip',
    mime_type: 'application/zip',
    page: 1,
    total_pages: 4,
    section: 'Пилотные данные',
    highlight: 'результаты пилотной установки',
    aliases: ['pilot_hl_nickel.zip'],
    pages: {
      1: {
        raw_text:
          'Архив содержит результаты пилотной установки по гидрометаллургии никеля: отчёты, таблицы измерений и протоколы отбора проб.',
        highlight: 'результаты пилотной установки',
      },
      2: {
        raw_text:
          'В комплект входят суточные журналы параметров, расчёт материального баланса и сводка отклонений от проектных значений.',
      },
    },
  },
  'span-10': {
    id: 'span-10',
    title: 'public_review_2023.pdf',
    file_name: 'public_review_2023.pdf',
    mime_type: 'application/pdf',
    page: 2,
    total_pages: 10,
    section: 'Обзор практик',
    highlight: 'публичный обзор технологий',
    aliases: ['public_review_2023.pdf'],
    pages: {
      1: {
        raw_text:
          'Публичный обзор подготовлен для внешних партнёров и содержит обезличенные сравнения технологических подходов.',
      },
      2: {
        raw_text:
          'Публичный обзор технологий охватывает мировые тренды в области обогащения, гидрометаллургии и утилизации отходов.',
        highlight: 'публичный обзор технологий',
      },
      3: {
        raw_text:
          'Для каждого направления приведены показатели энергоёмкости, водопотребления и типовые риски внедрения.',
      },
    },
  },
};

function normalizeKey(value) {
  return String(value ?? '')
    .trim()
    .toLowerCase();
}

const ALIAS_MAP = {};

Object.values(SOURCE_ENTRIES).forEach((entry) => {
  [entry.id, entry.title, entry.file_name, ...(entry.aliases ?? [])].forEach((key) => {
    const normalized = normalizeKey(key);
    if (normalized) ALIAS_MAP[normalized] = entry;
  });
});

export function getSourceById(id) {
  if (!id) return null;
  return SOURCE_ENTRIES[id] ?? ALIAS_MAP[normalizeKey(id)] ?? null;
}

export function resolveSourceRef(ref) {
  if (!ref) return null;
  if (typeof ref === 'object') {
    return (
      getSourceById(ref.source_span_id) ??
      getSourceById(ref.source_ref) ??
      getSourceById(ref.title) ??
      getSourceById(ref.file_name) ??
      (ref.author && ref.date ? getSourceById(`${ref.author}, ${ref.date}`) : null) ??
      (ref.author ? getSourceById(ref.author) : null)
    );
  }
  return getSourceById(ref);
}

export function getSourcePageNumbers(entry) {
  if (!entry) return [];
  const fromPages = entry.pages ? Object.keys(entry.pages).map(Number) : [];
  const merged = new Set([...fromPages, entry.page].filter(Boolean));
  return [...merged].sort((a, b) => a - b);
}

export function getSourcePageContent(entry, pageNum) {
  if (!entry) return { raw_text: '', highlight: null };
  const page = pageNum ?? entry.page;
  const pageData = entry.pages?.[page];
  if (pageData) {
    return {
      raw_text: pageData.raw_text,
      highlight: pageData.highlight ?? (page === entry.page ? entry.highlight : null),
    };
  }
  if (page === entry.page) {
    return { raw_text: entry.raw_text ?? '', highlight: entry.highlight ?? null };
  }
  return { raw_text: '', highlight: null };
}

export function getFullDocumentPages(entry) {
  if (!entry) return [];
  const knownNumbers = getSourcePageNumbers(entry);
  const total = entry.total_pages ?? Math.max(...knownNumbers, entry.page ?? 1, 1);
  const pages = [];

  for (let page = 1; page <= total; page += 1) {
    const { raw_text: rawText, highlight } = getSourcePageContent(entry, page);
    pages.push({
      page,
      raw_text: rawText || `Страница ${page}`,
      highlight,
      section: page === entry.page ? entry.section : null,
    });
  }

  return pages;
}

export function mergeSourceSpan(span) {
  if (!span?.id) return span;
  const catalog = getSourceById(span.id);
  if (!catalog) return span;
  return { ...catalog, ...span };
}

export { SOURCE_ENTRIES };
