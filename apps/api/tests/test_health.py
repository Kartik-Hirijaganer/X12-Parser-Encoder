from fastapi.testclient import TestClient


def test_healthcheck(client: TestClient) -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"]
    assert response.json()["status"] == "ok"


def test_deep_healthcheck(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["checks"]["library_import"] is True
    assert payload["checks"]["parser_smoke"] is True
    assert payload["checks"]["prometheus_metrics"] is True
    assert "dc_medicaid" in payload["checks"]["profiles_loaded"]
