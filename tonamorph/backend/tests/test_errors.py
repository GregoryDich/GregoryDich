from collections.abc import Callable

from fastapi.testclient import TestClient

from app.errors import ApiException


def test_unauthenticated_route_uses_contract_envelope(client: TestClient) -> None:
    response = client.get("/v1/me")
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "unauthorized"
    assert set(body["error"]) == {"code", "message", "details"}


def test_unknown_route_uses_contract_envelope(client: TestClient) -> None:
    response = client.get("/v1/nope")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_validation_error_envelope(client: TestClient, mint_jwt: Callable[..., str]) -> None:
    headers = {"Authorization": f"Bearer {mint_jwt()}"}
    response = client.get("/v1/credits/ledger", params={"limit": 0}, headers=headers)
    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "validation_error"
    assert body["details"]["errors"][0]["loc"] == ["query", "limit"]
    assert "input" not in body["details"]["errors"][0]


def test_api_exception_defaults() -> None:
    exc = ApiException("insufficient_credits", details={"available": 0})
    assert exc.status == 402
    assert exc.envelope().model_dump() == {
        "error": {
            "code": "insufficient_credits",
            "message": "Insufficient credits.",
            "details": {"available": 0},
        }
    }
