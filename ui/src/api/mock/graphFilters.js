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
  const links = subgraph.links.filter(
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
