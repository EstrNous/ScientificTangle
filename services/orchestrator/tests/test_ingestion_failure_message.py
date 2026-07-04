from app.service.service import format_ingestion_failure_message


def test_format_ingestion_failure_message_prefers_unsupported_warnings() -> None:
    warnings = [
        "retry: normalize",
        "unsupported_source_format: application/x-old",
        "unsupported_source_format: text/plain",
    ]
    message = format_ingestion_failure_message("ingestion_failed", "normalize error", warnings)
    assert message.startswith("ingestion_failed: normalize error;")
    assert "unsupported_source_format: application/x-old" in message
    assert "retry: normalize" not in message


def test_format_ingestion_failure_message_without_warnings() -> None:
    message = format_ingestion_failure_message("timeout", "downstream unavailable", [])
    assert message == "timeout: downstream unavailable"
