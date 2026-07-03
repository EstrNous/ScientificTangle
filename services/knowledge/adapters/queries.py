WRITE_DOCUMENT = """
MERGE (d:Document {document_id: $document_id})
SET d.title = $title,
    d.source_type = $source_type,
    d.access_level = $access_level,
    d.language = $language
"""

WRITE_SOURCE_SPAN = """
MERGE (s:SourceSpan {source_span_id: $source_span_id})
SET s.document_id = $document_id,
    s.page_number = $page_number,
    s.raw_text = $raw_text,
    s.char_start = $char_start,
    s.char_end = $char_end,
    s.source_type = $source_type,
    s.table_block_id = $table_block_id
WITH s
MATCH (d:Document {document_id: $document_id})
MERGE (s)-[:PART_OF]->(d)
"""

WRITE_ENTITY = """
MERGE (e:Entity {entity_id: $entity_id})
SET e.canonical_name = $canonical_name,
    e.domain_type = $domain_type,
    e.created_at = coalesce(e.created_at, $created_at)
"""

WRITE_ALIAS = """
MERGE (a:Alias {alias_id: $alias_id})
SET a.name = $name,
    a.type = $type,
    a.confidence = $confidence
WITH a
MATCH (e:Entity {entity_id: $entity_id})
MERGE (e)-[:HAS_ALIAS]->(a)
"""

WRITE_MEASUREMENT = """
MERGE (m:Measurement {measurement_id: $measurement_id})
SET m.raw_text = $raw_text,
    m.operator = $operator,
    m.value = $value,
    m.min = $min,
    m.max = $max,
    m.unit = $unit,
    m.normalized_value = $normalized_value,
    m.normalized_unit = $normalized_unit,
    m.uncertainty = $uncertainty,
    m.dimension = $dimension
"""

WRITE_GEOGRAPHY = """
MERGE (g:Geography {geo_id: $geo_id})
SET g.name = $name,
    g.type = $type,
    g.precision = $precision
"""

WRITE_CLAIM = """
MERGE (c:Claim {claim_id: $claim_id})
SET c.claim_version = coalesce(c.claim_version, 0) + 1,
    c.status = $status,
    c.confidence = $confidence,
    c.statement = $statement,
    c.experiment_performed_at = $experiment_performed_at,
    c.source_published_at = $source_published_at,
    c.claim_extracted_at = $claim_extracted_at,
    c.claim_last_updated_at = $claim_last_updated_at,
    c.latest_supporting_evidence_date = $latest_supporting_evidence_date,
    c.supersedes_claim_id = $supersedes_claim_id,
    c.updated_reason = $updated_reason
WITH c
FOREACH (_ IN CASE WHEN $supersedes_claim_id IS NULL THEN [] ELSE [1] END |
    MERGE (prev:Claim {claim_id: $supersedes_claim_id})
    MERGE (c)-[:SUPERSEDES]->(prev)
)
WITH c
FOREACH (span_id IN $source_span_ids |
    MERGE (s:SourceSpan {source_span_id: span_id})
    MERGE (c)-[:DESCRIBED_IN]->(s)
)
WITH c
FOREACH (measurement_id IN $measurement_ids |
    MATCH (m:Measurement {measurement_id: measurement_id})
    MERGE (c)-[:QUANTIFIED_BY]->(m)
)
WITH c
FOREACH (geo_id IN $geo_ids |
    MATCH (g:Geography {geo_id: geo_id})
    MERGE (c)-[:APPLIED_IN_GEOGRAPHY]->(g)
)
WITH c
FOREACH (entity_id IN $entity_ids |
    MATCH (e:Entity {entity_id: entity_id})
    MERGE (c)-[:VALIDATED_BY]->(e)
)
"""

WRITE_SEMANTIC_RELATION = """
MATCH (c:Claim {claim_id: $claim_id})
MATCH (e:Entity {entity_id: $target_id})
CALL apoc.merge.relationship(c, $rel_type, {}, {}, e, {}) YIELD rel
RETURN rel
"""

WRITE_SEMANTIC_RELATION_FALLBACK = """
MATCH (c:Claim {claim_id: $claim_id})
MATCH (e:Entity {entity_id: $target_id})
CALL {
    WITH c, e
    CALL db.createRelationship(c, $rel_type, {}, e) YIELD rel
    RETURN rel
} IN TRANSACTIONS OF 1 ROW
RETURN count(*) AS created
"""

WRITE_SEMANTIC_RELATION_SIMPLE = """
MATCH (c:Claim {claim_id: $claim_id})
MATCH (e:Entity {entity_id: $target_id})
MERGE (c)-[r:RELATED_TO]->(e)
SET r.semantic_type = $rel_type
"""

WRITE_FACT_VERSION = """
MATCH (c:Claim {claim_id: $claim_id})
CREATE (fv:FactVersion {
    fact_version_id: $fact_version_id,
    claim_id: $claim_id,
    version: c.claim_version,
    status: c.status,
    recorded_at: $recorded_at
})
MERGE (c)-[:HAS_VERSION]->(fv)
"""

WRITE_CANDIDATE_ENTITY = """
MERGE (ce:CandidateEntity {candidate_id: $candidate_id})
SET ce.raw_data = $raw_data,
    ce.extracted_at = $extracted_at
"""

RESOLVE_ALIAS_FULLTEXT = """
CALL db.index.fulltext.queryNodes('alias_name_ft', $mention + '*') YIELD node, score
MATCH (e:Entity)-[:HAS_ALIAS]->(node)
RETURN DISTINCT e.entity_id AS entity_id, score
ORDER BY score DESC
LIMIT $limit
"""

RESOLVE_ALIAS_CONTAINS = """
MATCH (a:Alias)
WHERE toLower(a.name) CONTAINS toLower($mention)
MATCH (e:Entity)-[:HAS_ALIAS]->(a)
RETURN DISTINCT e.entity_id AS entity_id
LIMIT $limit
UNION
MATCH (e:Entity)
WHERE toLower(e.canonical_name) CONTAINS toLower($mention)
RETURN DISTINCT e.entity_id AS entity_id
LIMIT $limit
"""

FIND_CONFLICTS = """
MATCH (e:Entity {entity_id: $entity_id})<-[:VALIDATED_BY|RELATED_TO]-(c:Claim)-[:QUANTIFIED_BY]->(m:Measurement)
MATCH (e)<-[:VALIDATED_BY|RELATED_TO]-(c2:Claim)-[:QUANTIFIED_BY]->(m2:Measurement)
WHERE c.claim_id < c2.claim_id
  AND (
    EXISTS { (c)-[:CONTRADICTS]->(c2) }
    OR (m.value IS NOT NULL AND m2.value IS NOT NULL AND m.unit = m2.unit AND m.value <> m2.value)
    OR (m.min IS NOT NULL AND m2.max IS NOT NULL AND m.min > m2.max)
  )
RETURN c.claim_id AS claim_id_a, c2.claim_id AS claim_id_b,
       collect(DISTINCT m.measurement_id) + collect(DISTINCT m2.measurement_id) AS measurement_ids,
       'measurement_mismatch' AS reason
LIMIT 50
"""

FIND_MISSING_EDGES = """
MATCH (proc:Entity)
WHERE proc.domain_type = 'Process'
MATCH (mat:Entity)
WHERE mat.domain_type IN ['Material', 'Substance']
OPTIONAL MATCH (proc)<-[:VALIDATED_BY|RELATED_TO]-(c:Claim)-[:USES_MATERIAL|RELATED_TO]->(mat)
OPTIONAL MATCH (c)-[:QUANTIFIED_BY]->(m:Measurement)
WITH proc, mat, count(m) AS measurement_count
WHERE measurement_count = 0
RETURN proc.entity_id AS process_id,
       mat.entity_id AS material_id,
       'missing_output_measurement' AS gap_type
LIMIT 50
"""

EXPAND_NEIGHBORS = """
MATCH (center:Entity {entity_id: $entity_id})
CALL {
    WITH center
    MATCH path = (center)-[*1..$depth]-(neighbor)
    WHERE neighbor:Entity OR neighbor:Claim OR neighbor:Measurement OR neighbor:SourceSpan OR neighbor:Document
    RETURN path
    LIMIT $limit
}
RETURN path
LIMIT $limit
"""

BUILD_SUBGRAPH = """
MATCH (e:Entity)
WHERE e.entity_id IN $entity_ids OR toLower(e.canonical_name) IN [hint IN $entity_hints | toLower(hint)]
MATCH (c:Claim)-[:DESCRIBED_IN]->(s:SourceSpan)-[:PART_OF]->(d:Document)
WHERE (c)-[:VALIDATED_BY|RELATED_TO]->(e)
  AND d.access_level IN $access_levels
RETURN DISTINCT e, c, s, d
LIMIT $limit
"""

FIND_ENTITIES = """
MATCH (e:Entity)
WHERE ($name IS NULL OR toLower(e.canonical_name) CONTAINS toLower($name))
  AND ($domain_type IS NULL OR e.domain_type = $domain_type)
RETURN e
ORDER BY e.canonical_name
LIMIT $limit
"""

FILTER_BY_CONSTRAINTS = """
MATCH (c:Claim)-[:DESCRIBED_IN]->(s:SourceSpan)-[:PART_OF]->(d:Document)
OPTIONAL MATCH (c)-[:QUANTIFIED_BY]->(m:Measurement)
OPTIONAL MATCH (c)-[:APPLIED_IN_GEOGRAPHY]->(g:Geography)
WHERE d.access_level IN $access_levels
  AND ($min_confidence IS NULL OR c.confidence >= $min_confidence)
  AND ($status IS NULL OR c.status = $status)
  AND ($geo_name IS NULL OR toLower(g.name) CONTAINS toLower($geo_name))
  AND ($numeric_min IS NULL OR m.normalized_value >= $numeric_min)
  AND ($numeric_max IS NULL OR m.normalized_value <= $numeric_max)
  AND ($published_after IS NULL OR c.source_published_at >= $published_after)
  AND ($published_before IS NULL OR c.source_published_at <= $published_before)
RETURN DISTINCT c, s, d, m, g
LIMIT $limit
"""

AGGREGATE_MEASUREMENTS = """
MATCH (c:Claim)-[:QUANTIFIED_BY]->(m:Measurement)
WHERE ($entity_id IS NULL OR EXISTS {
    MATCH (e:Entity {entity_id: $entity_id})<-[:VALIDATED_BY|RELATED_TO]-(c)
})
RETURN coalesce(m.dimension, m.unit, 'default') AS group_key,
       count(m) AS count,
       avg(m.normalized_value) AS avg_value,
       min(m.normalized_value) AS min_value,
       max(m.normalized_value) AS max_value,
       coalesce(max(m.normalized_unit), max(m.unit), '') AS unit
"""

COMPARE_GROUPS = """
MATCH (c:Claim)-[:QUANTIFIED_BY]->(m:Measurement)
WHERE coalesce(m.dimension, m.unit, 'default') IN [$group_a_key, $group_b_key]
RETURN coalesce(m.dimension, m.unit, 'default') AS group_key,
       avg(m.normalized_value) AS avg_value,
       coalesce(max(m.normalized_unit), max(m.unit), '') AS unit
"""

RETRIEVE_EVIDENCE = """
MATCH (c:Claim)-[:DESCRIBED_IN]->(s:SourceSpan)-[:PART_OF]->(d:Document)
WHERE d.access_level IN $access_levels
  AND (
    size($entity_hints) = 0
    OR EXISTS {
        MATCH (e:Entity)<-[:VALIDATED_BY|RELATED_TO]-(c)
        WHERE toLower(e.canonical_name) IN [hint IN $entity_hints | toLower(hint)]
           OR e.entity_id IN $entity_hints
    }
  )
RETURN c, s, d
ORDER BY c.confidence DESC, c.claim_last_updated_at DESC
LIMIT $limit
"""

RANK_CLAIMS = """
UNWIND $claim_ids AS claim_id
MATCH (c:Claim {claim_id: claim_id})
RETURN c.claim_id AS claim_id,
       c.status AS status,
       c.confidence AS confidence,
       c.source_published_at AS source_published_at,
       c.latest_supporting_evidence_date AS latest_supporting_evidence_date,
       c.claim_last_updated_at AS claim_last_updated_at
"""

PING = "RETURN 1 AS ok"
