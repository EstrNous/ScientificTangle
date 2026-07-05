import json
from pathlib import Path


def test_official_gold_questions_have_reviewed_source_spans() -> None:
    gold = json.loads(Path("eval/gold_questions.json").read_text(encoding="utf-8"))
    fixtures = json.loads(Path("eval/reviewed_source_fixtures.json").read_text(encoding="utf-8"))
    reviewed = {item["question_id"]: item for item in fixtures["official_questions"]}

    official = [item for item in gold["questions"] if item["split"] == "mvp"]

    assert len(official) == 4
    for question in official:
        fixture = reviewed[question["id"]]
        assert question["expected_source_span_ids"] == fixture["expected_source_span_ids"]
        assert question["expected_source_span_review"]["status"] == "reviewed"
        assert fixture["source_candidates"]
        assert all(candidate["highlight_end"] > candidate["highlight_start"] for candidate in fixture["source_candidates"])


def test_full_dataset_status_is_explicitly_candidate_or_blocked() -> None:
    fixtures = json.loads(Path("eval/reviewed_source_fixtures.json").read_text(encoding="utf-8"))

    assert fixtures["external_dataset"]["status"] == "available_raw_corpus"
    assert fixtures["external_dataset"]["normalized_source_spans_status"] == "blocked_by_data"
    assert fixtures["external_dataset"]["file_count"] >= 1453
    for item in fixtures["official_questions"]:
        assert item["full_corpus_status"] in {"candidate", "blocked_by_data"}
        assert item["full_corpus_reason_codes"]


def test_review_gap_conflict_fixtures_use_reason_codes() -> None:
    fixtures = json.loads(Path("eval/reviewed_source_fixtures.json").read_text(encoding="utf-8"))

    for section in ("review_queue_fixtures", "gap_fixtures", "conflict_fixtures"):
        assert fixtures[section]
        for item in fixtures[section]:
            if item["status"] in {"candidate", "deferred", "blocked_by_data"}:
                assert item["reason_codes"]
