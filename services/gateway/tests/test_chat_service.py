from app.service.chat_service import ChatService


def test_map_query_response_builds_ui_payload() -> None:
    payload = ChatService._map_query_response(
        {
            "answer": {
                "answer_text": "Тестовый ответ",
                "confidence": 0.77,
            },
            "query_ir": {"entities": ["никель", "католит"]},
            "evidence_bundle": {
                "evidence_items": [
                    {
                        "source_span": {
                            "document_id": "nickel_report.pdf",
                            "page": 12,
                            "text": "скорость потока католита составляет 2–4 м/ч",
                        }
                    }
                ]
            },
            "warnings": ["demo_warning"],
        }
    )

    assert payload["content"] == "Тестовый ответ"
    assert payload["confidence"] == 0.77
    assert payload["sources"][0]["title"] == "nickel_report.pdf"
    assert payload["evidence_table"]["rows"][0][2] == "nickel_report.pdf"
    assert payload["expanded_synonyms"] == ["никель", "католит"]
