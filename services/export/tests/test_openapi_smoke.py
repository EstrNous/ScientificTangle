from app.main import app


def test_health_routes_are_in_openapi() -> None:
    paths = app.openapi()["paths"]
    assert "/health" in paths
    assert "/ready" in paths
