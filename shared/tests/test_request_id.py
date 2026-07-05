import re

from shared.utils.request_id import generate_request_id


def test_generate_request_id_format() -> None:
    value = generate_request_id()
    assert re.match(r"^[A-Za-z0-9._-]{8,128}$", value)
