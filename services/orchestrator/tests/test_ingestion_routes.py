from app.main import app


def _route_method_index(app_instance, path: str, method: str) -> int:
    for index, route in enumerate(app_instance.routes):
        route_path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if route_path == path and methods and method in methods:
            return index
    raise AssertionError(f"Route {method} {path} is not registered")


def test_ingestion_create_route_is_registered_before_get_task() -> None:
    create_index = _route_method_index(app, "/ingestion/tasks", "POST")
    get_index = _route_method_index(app, "/ingestion/tasks/{task_id}", "GET")
    assert create_index < get_index


def test_ingestion_routes_are_in_openapi() -> None:
    paths = app.openapi()["paths"]
    assert "/ingestion/tasks" in paths
    assert "/ingestion/tasks/{task_id}" in paths
    assert paths["/ingestion/tasks"]["post"]["responses"]["202"]
    assert paths["/ingestion/tasks/{task_id}"]["get"]["responses"]["200"]
