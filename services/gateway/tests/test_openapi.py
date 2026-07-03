from app.main import app


def test_upload_and_task_routes_are_in_openapi() -> None:
    paths = app.openapi()["paths"]

    assert "/documents/upload" in paths
    assert "/tasks/{task_id}" in paths
    assert "/chat/sessions" in paths
    assert "/chat/sessions/{session_id}/messages" in paths
    assert "/graph" in paths
    assert "/search" in paths
    assert paths["/documents/upload"]["post"]["responses"]["202"]
