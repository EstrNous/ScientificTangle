const GEO_MAP = {
  domestic: ['отечественная', 'domestic', 'россия', 'russia'],
  foreign: ['зарубежная', 'foreign', 'international'],
  unknown: ['неизвестно', 'unknown'],
};

function matchesGeo(item, geoFilter) {
  if (geoFilter === 'all') return true;
  const aliases = GEO_MAP[geoFilter] ?? [];
  const value = String(item.geoKey ?? item.geo ?? '').toLowerCase();
  return aliases.some((alias) => value.includes(alias));
}

export function filterGraphSearchResults(items, { query, material, process, geo }) {
  const normalizedQuery = query.trim().toLowerCase();

  return items.filter((item) => {
    if (material !== 'all' && item.material !== material) return false;
    if (process !== 'all' && item.process !== process) return false;
    if (!matchesGeo(item, geo)) return false;

    if (!normalizedQuery) return true;

    const haystack = [item.title, item.material, item.process, item.geo, item.geoKey]
      .filter(Boolean)
      .join(' ')
      .toLowerCase();

    return haystack.includes(normalizedQuery);
  });
}
