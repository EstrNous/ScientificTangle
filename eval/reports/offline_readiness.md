# Offline quality readiness report

- Schema version: offline_quality_gate.v1
- Generated at: 2026-07-04T10:39:37.613526+00:00
- Overall status: warn
- Official questions: 4
- Corpus regression questions: 12
- Live model calls: blocked_by_policy

## Checks

- pinned_input_integrity: pass
- regression_suite_inventory: pass
- no_live_policy_declared: pass
- official_expected_source_spans: pass
- official_query_ir_constraints: pass
- access_filtering_fixture: pass
- offline_e2e_scenario_inventory: pass
- full_corpus_reviewed_source_expectations: blocked_by_data
- live_answer_quality: blocked_by_policy
- live_latency_p95: blocked_by_policy

## Deferred

- live_answer_quality: blocked_by_policy
- live_latency_p95: blocked_by_policy
- full_corpus_source_expectations: blocked_by_data
