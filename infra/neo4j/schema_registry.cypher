MERGE (sv:SchemaVersion {version: 'neo4j_mvp_v1'}) SET sv.status = 'registry_seed', sv.applied_at = datetime();
