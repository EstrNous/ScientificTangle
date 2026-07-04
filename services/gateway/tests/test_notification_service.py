from uuid import uuid4

from app.service.notification_service import TYPE_TITLES, NotificationService


class FakeNotification:
    def __init__(self) -> None:
        self.id = uuid4()
        self.type = "interest_match"
        self.message = "Совпадение с подпиской: никель, католит"
        self.reference_id = "nickel_report.pdf"
        self.is_read = False
        self.created_at = FakeNotification._now()

    @staticmethod
    def _now():
        from datetime import UTC, datetime

        return datetime(2026, 7, 4, 5, 10, tzinfo=UTC)


def test_notification_payload_maps_ui_fields() -> None:
    note = FakeNotification()
    payload = NotificationService._payload(note)

    assert payload.title == TYPE_TITLES["interest_match"]
    assert payload.reason == note.message
    assert payload.reference_id == "nickel_report.pdf"
    assert payload.read is False
    assert payload.created_at.isoformat().startswith("2026-07-04")
