from app.main import app


def _route_method_index(app_instance, path: str, method: str) -> int:
    for index, route in enumerate(app_instance.routes):
        route_path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if route_path == path and methods and method in methods:
            return index
    raise AssertionError(f"Route {method} {path} is not registered")


def test_upload_route_is_registered_before_delete_document() -> None:
    upload_index = _route_method_index(app, "/documents/upload", "POST")
    delete_index = _route_method_index(app, "/documents/{document_id}", "DELETE")
    assert upload_index < delete_index


def test_upload_and_task_routes_are_in_openapi() -> None:
    paths = app.openapi()["paths"]

    assert "/documents/upload" in paths
    assert "/tasks/{task_id}" in paths
    assert "/documents/{document_id}" in paths
    assert "/chat/sessions" in paths
    assert "/chat/sessions/{session_id}/messages" in paths
    assert "/interests" in paths
    assert "/notifications" in paths
    assert "/notifications/read-all" in paths
    assert "/graph" in paths
    assert "/search" in paths
    assert paths["/documents/upload"]["post"]["responses"]["202"]
    assert paths["/documents/{document_id}"]["get"]["responses"]["200"]
    assert paths["/documents/{document_id}"]["delete"]["responses"]["200"]


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


def test_dictionary_routes_are_in_openapi() -> None:
    paths = app.openapi()["paths"]
    assert paths["/dictionaries/upload"]["post"]["responses"]["202"]
    assert "/dictionaries" in paths
    assert "/dictionaries/active" in paths
    assert "/dictionaries/{version_id}/activate" in paths


def test_e1_backend_contract_routes_are_in_openapi() -> None:
    paths = app.openapi()["paths"]

    assert paths["/interests"]["get"]["responses"]["200"]
    assert paths["/interests"]["put"]["responses"]["200"]
    assert paths["/notifications"]["get"]["responses"]["200"]
    assert paths["/notifications/{notification_id}/read"]["post"]["responses"]["200"]
    assert paths["/review/queue"]["get"]["responses"]["200"]
    assert paths["/review/queue"]["post"]["responses"]["200"]
    assert paths["/review/decisions"]["post"]["responses"]["200"]
    assert paths["/eval/report/summary"]["get"]["responses"]["200"]
