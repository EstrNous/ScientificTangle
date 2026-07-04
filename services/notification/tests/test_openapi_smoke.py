from app.api.factory import create_app


def test_health_routes_are_in_openapi() -> None:
    app = create_app()
    paths = app.openapi()["paths"]
    assert "/health" in paths
    assert "/ready" in paths
    assert "/interests" in paths
    assert "/notifications" in paths
    assert "/internal/v1/events" in paths
    assert "/internal/v1/match" in paths
