from fastapi.testclient import TestClient


def test_health_ok(client: TestClient) -> None:
    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_unversioned_alias(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_request_id_is_echoed(client: TestClient) -> None:
    response = client.get("/v1/health", headers={"X-Request-ID": "abc-123"})
    assert response.headers["x-request-id"] == "abc-123"


def test_request_id_is_generated(client: TestClient) -> None:
    response = client.get("/v1/health")
    assert len(response.headers["x-request-id"]) == 32
