import uuid


def generate_request_id() -> str:
    return uuid.uuid4().hex
