from app.main import app


def test_upload_and_normalization_routes_are_in_openapi() -> None:
    schema = app.openapi()

    assert "/ingestion/tasks/{task_id}/sources" in schema["paths"]
    assert "/ingestion/tasks/{task_id}/normalize" in schema["paths"]
    response_schema = schema["paths"]["/ingestion/tasks/{task_id}/normalize"]["post"][
        "responses"
    ]["200"]["content"]["application/json"]["schema"]
    assert response_schema["$ref"].endswith("NormalizeStoredSourcesResponse")
