from app.main import app


def _openapi_path_index(app_instance, path: str) -> int:
    paths = app_instance.openapi()["paths"]
    if path not in paths:
        raise AssertionError(f"Path {path} is not registered in OpenAPI")
    return list(paths).index(path)


def test_ingestion_create_route_is_registered_before_get_task() -> None:
    create_index = _openapi_path_index(app, "/ingestion/tasks")
    get_index = _openapi_path_index(app, "/ingestion/tasks/{task_id}")
    assert create_index < get_index


def test_ingestion_routes_are_in_openapi() -> None:
    paths = app.openapi()["paths"]
    assert "/ingestion/tasks" in paths
    assert "/ingestion/tasks/{task_id}" in paths
    assert paths["/ingestion/tasks"]["post"]["responses"]["202"]
    assert paths["/ingestion/tasks/{task_id}"]["get"]["responses"]["200"]
