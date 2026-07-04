from app.service.ingestion_notifications import match_artifacts_from_extraction


def test_match_artifacts_from_extraction_collects_confirmed_and_candidates() -> None:
    artifacts = match_artifacts_from_extraction(
        {
            "confirmed": [
                {
                    "id": "a1",
                    "kind": "material",
                    "value": "никель",
                    "status": "confirmed",
                    "confidence": 0.9,
                }
            ],
            "candidates": [
                {
                    "id": "a2",
                    "kind": "claim",
                    "value": "recovery",
                    "status": "candidate",
                    "confidence": 0.5,
                    "reason_codes": ["low_confidence"],
                }
            ],
        }
    )
    assert len(artifacts) == 2
    assert artifacts[0]["id"] == "a1"
    assert artifacts[1]["id"] == "a2"


def test_match_artifacts_from_extraction_skips_invalid_items() -> None:
    assert match_artifacts_from_extraction({"confirmed": [{"kind": "claim"}]}) == []
    assert match_artifacts_from_extraction({}) == []
    assert match_artifacts_from_extraction("invalid") == []
