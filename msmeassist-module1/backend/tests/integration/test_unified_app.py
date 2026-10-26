from fastapi.testclient import TestClient

from app.unified_main import app


def test_unified_app_exposes_single_localhost_entrypoints():
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200, health.text

    route_paths = {route.path for route in app.routes}
    assert "/api/recommendations/rank" in route_paths
    assert "/api/sources" in route_paths
    assert "/api/workflow/decision" in route_paths
