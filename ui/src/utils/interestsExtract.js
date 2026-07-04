const INTEREST_GROUPS = {
  materials: ['никель', 'медь', 'кобальт', 'платина', 'золото', 'железо', 'руда'],
  processes: [
    'флотация',
    'электроэкстракция',
    'гидрометаллургия',
    'пирометаллургия',
    'обессоливание',
    'водоочистка',
    'газоочистка',
    'циркуляция',
  ],
  equipment: ['колонна', 'реактор', 'фильтр', 'электролизёр'],
  properties: ['извлечение', 'селективность', 'эффективность'],
  geography: ['россия', 'китай', 'канада', 'австралия', 'отечественн', 'зарубежн'],
};

const CHEMICAL_PATTERN = /\b[A-Z][a-z]?[0-9]*(?:[A-Z][a-z]?[0-9]*)+\b/g;

export function extractInterests(text) {
  const lowered = text.toLowerCase();
  const interests = [];

  for (const [label, terms] of Object.entries(INTEREST_GROUPS)) {
    const matched = terms.filter((term) => lowered.includes(term));
    if (matched.length > 0) {
      interests.push({
        label,
        weight: Math.min(1, 0.35 + 0.1 * matched.length),
        source_terms: matched.slice(0, 8),
      });
    }
  }

  const formulas = text.match(CHEMICAL_PATTERN) ?? [];
  for (const formula of formulas) {
    interests.push({
      label: `substance:${formula}`,
      weight: 0.8,
      source_terms: [formula],
    });
  }

  return interests;
}
