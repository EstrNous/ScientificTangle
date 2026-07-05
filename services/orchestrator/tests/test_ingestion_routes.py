from app.main import app


def test_ingestion_create_route_is_registered_before_get_task() -> None:
    ordered: list[tuple[int, str, frozenset[str]]] = []
    for index, route in enumerate(app.routes):
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if path in {"/ingestion/tasks", "/ingestion/tasks/{task_id}"} and methods:
            ordered.append((index, path, frozenset(methods)))
    create_index = next(
        index for index, path, methods in ordered if path == "/ingestion/tasks" and "POST" in methods
    )
    get_index = next(
        index
        for index, path, methods in ordered
        if path == "/ingestion/tasks/{task_id}" and "GET" in methods
    )
    assert create_index < get_index


def test_ingestion_routes_are_in_openapi() -> None:
    paths = app.openapi()["paths"]
    assert "/ingestion/tasks" in paths
    assert "/ingestion/tasks/{task_id}" in paths
    assert paths["/ingestion/tasks"]["post"]["responses"]["202"]
    assert paths["/ingestion/tasks/{task_id}"]["get"]["responses"]["200"]
