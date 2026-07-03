from app.main import app


def test_graph_routes_are_in_openapi() -> None:
    paths = app.openapi()["paths"]

    assert "/graph" in paths
    assert "/search" in paths
    assert paths["/graph"]["get"]["responses"]["200"]
    assert paths["/search"]["get"]["responses"]["200"]
