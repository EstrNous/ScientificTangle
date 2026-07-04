from app.main import app


def test_upload_and_task_routes_are_in_openapi() -> None:
    paths = app.openapi()["paths"]

    assert "/documents/upload" in paths
    assert "/tasks/{task_id}" in paths
    assert "/chat/sessions" in paths
    assert "/chat/sessions/{session_id}/messages" in paths
    assert "/notifications" in paths
    assert "/graph" in paths
    assert "/search" in paths
    assert paths["/documents/upload"]["post"]["responses"]["202"]


def test_query_e2e_routes_are_in_openapi() -> None:
    paths = app.openapi()["paths"]

    assert "/query" in paths
    assert "/runs/{run_id}" in paths
    assert "/export" in paths
    assert "/source/{source_span_id}" in paths
    assert "/graph/subgraph" in paths
    assert "/search" in paths
    schema = app.openapi()["components"]["schemas"]["QueryRequest"]
    assert "documents" not in schema["properties"]
