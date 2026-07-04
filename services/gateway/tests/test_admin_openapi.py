from app.main import app


def test_admin_and_strategic_routes_are_in_openapi() -> None:
    paths = app.openapi()["paths"]

    assert "/admin" in paths
    assert "/admin/stats" in paths
    assert "/audit/events" in paths
    assert "/strategic/metrics" in paths
    assert "/strategic/evaluation" in paths
    assert "/lab/coverage" in paths
    assert paths["/admin"]["get"]["responses"]["200"]
    assert paths["/strategic/metrics"]["get"]["responses"]["200"]
