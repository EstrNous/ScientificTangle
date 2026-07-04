# Qdrant MVP schema

Retrieval service owns MVP collection `st_evidence_v1`.

Vector:
- `size`: 256
- `distance`: `Cosine`
- source: model service `/v1/embeddings`

Payload indexes created by `POST /v1/index/bootstrap`:
- keyword: `item_type`, `document_id`, `source_span_id`, `source_type`, `access_level`, `allowed_roles`, `table_block_id`, `table_row_id`, `units`, `geo_bucket`, `geo_country`, `claim_ids`, `graph_entity_ids`, `dictionary_version_id`
- integer: `page`, `highlight_start`, `highlight_end`, `published_year`
- float: `numeric_min`, `numeric_max`

Required payload fields:
- `text`
- `document_id`
- `source_span_id`
- `source_type`
- `access_level`
- `allowed_roles`
- `page`
- `highlight_start`
- `highlight_end`
- `table_row_id` (for table rows; empty string for text spans)
- `numeric_values`
- `units`
- `geo_bucket`
- `claim_ids`
- `graph_entity_ids`
- `dictionary_version_id`
- `document_metadata`
