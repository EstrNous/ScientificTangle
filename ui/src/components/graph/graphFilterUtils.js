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

export function filterSubgraphByNodeTypes(subgraph, activeTypes, query = '') {
  if (!subgraph?.nodes?.length) {
    return { nodes: [], links: [] };
  }

  const normalizedQuery = query.trim().toLowerCase();
  const typeSet = new Set(activeTypes);

  const nodes = subgraph.nodes.filter((node) => {
    if (!typeSet.has(node.type)) return false;
    if (!normalizedQuery) return true;
    const haystack = [node.label, node.type, node.id].join(' ').toLowerCase();
    return haystack.includes(normalizedQuery);
  });

  const nodeIds = new Set(nodes.map((n) => n.id));
  const links = (subgraph.links ?? []).filter(
    (link) => nodeIds.has(link.source) && nodeIds.has(link.target),
  );

  return { nodes, links };
}

export function filterEntitiesByNodeTypes(entities, activeTypes, query = '') {
  const normalizedQuery = query.trim().toLowerCase();
  const typeSet = new Set(activeTypes);

  return entities.filter((entity) => {
    if (!typeSet.has(entity.type)) return false;
    if (!normalizedQuery) return true;
    const haystack = [entity.name, entity.type].join(' ').toLowerCase();
    return haystack.includes(normalizedQuery);
  });
}
