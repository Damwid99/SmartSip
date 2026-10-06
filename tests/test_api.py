import datetime

from fastapi.testclient import TestClient


def register_payload(
    email: str = "api@example.com",
    username: str = "api-user",
) -> dict[str, object]:
    return {
        "email": email,
        "google_id": f"google-{email}",
        "profile": {
            "username": username,
            "gender": "male",
            "weight_kg": 80.0,
            "birth_date": "1995-01-01",
            "location": "Warszawa",
        },
    }


def register_and_login(
    client: TestClient,
    email: str = "api@example.com",
    username: str = "api-user",
) -> dict[str, str]:
    response = client.post("/users", json=register_payload(email, username))
    assert response.status_code == 201, response.text

    response = client.post(
        "/users/auth/google",
        json={"id_token": f"google-{email}"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_health_and_root_redirect(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/docs"


def test_registration_rejects_duplicate_email_and_username(client: TestClient):
    client.post("/users", json=register_payload())

    duplicate_email = register_payload(username="different-user")
    response = client.post("/users", json=duplicate_email)
    assert response.status_code == 400
    assert "email" in response.json()["detail"]

    duplicate_username = register_payload(email="other@example.com")
    response = client.post("/users", json=duplicate_username)
    assert response.status_code == 400
    assert "username" in response.json()["detail"]


def test_registration_validates_email_and_profile(client: TestClient):
    invalid_payload = register_payload()
    invalid_payload["email"] = "not-an-email"
    response = client.post("/users", json=invalid_payload)
    assert response.status_code == 422

    invalid_payload = register_payload(
        email="missing-google@example.com",
        username="missing-google",
    )
    del invalid_payload["google_id"]
    response = client.post("/users", json=invalid_payload)
    assert response.status_code == 422

    invalid_payload = register_payload(email="weight@example.com", username="weight-user")
    invalid_payload["profile"] = {**invalid_payload["profile"], "weight_kg": 10}
    response = client.post("/users", json=invalid_payload)
    assert response.status_code == 422


def test_google_login_and_protected_routes_require_valid_credentials(client: TestClient):
    headers = register_and_login(client)

    response = client.get("/users/me")
    assert response.status_code == 401

    response = client.post(
        "/users/auth/google",
        json={"id_token": "google-wrong@example.com"},
    )
    assert response.status_code == 401

    response = client.get("/users/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["profile"]["username"] == "api-user"


def test_google_login_rejects_invalid_google_token(client: TestClient, monkeypatch):
    def reject_token(token: str) -> dict[str, object]:
        raise ValueError("invalid token")

    monkeypatch.setattr("src.users.router.verify_google_token", reject_token)

    response = client.post(
        "/users/auth/google",
        json={"id_token": "invalid-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Niepoprawny token Google"


def test_profile_update_changes_only_supported_fields(client: TestClient):
    headers = register_and_login(client)

    response = client.patch(
        "/users/me/profile",
        json={"weight_kg": 91.5, "location": "Kraków"},
        headers=headers,
    )
    assert response.status_code == 200
    profile = response.json()
    assert profile["weight_kg"] == 91.5
    assert profile["location"] == "Kraków"
    assert profile["username"] == "api-user"


def test_catalog_lists_public_drinks_and_manages_custom_containers(client: TestClient):
    headers = register_and_login(client)

    response = client.get("/catalog/drinks")
    assert response.status_code == 200
    drinks = response.json()
    assert [drink["name"] for drink in drinks] == ["Kawa", "Woda"]

    response = client.get("/catalog/containers", headers=headers)
    assert response.status_code == 200
    containers = response.json()
    assert len(containers) == 1
    assert containers[0]["is_custom"] is False

    response = client.post(
        "/catalog/containers",
        json={"name": "Butelka", "volume_ml": 750, "icon": "🧴"},
        headers=headers,
    )
    assert response.status_code == 201
    container = response.json()
    assert container["is_custom"] is True
    assert container["user_id"] is not None

    response = client.get("/catalog/containers", headers=headers)
    assert response.status_code == 200
    assert any(item["id"] == container["id"] for item in response.json())

    response = client.delete(f"/catalog/containers/{container['id']}", headers=headers)
    assert response.status_code == 204
    assert response.content == b""

    response = client.delete(f"/catalog/containers/{container['id']}", headers=headers)
    assert response.status_code == 404


def test_catalog_container_validation_and_system_container_protection(client: TestClient):
    headers = register_and_login(client)

    response = client.get("/catalog/containers", headers=headers)
    assert response.status_code == 200
    system_container = next(item for item in response.json() if not item["is_custom"])
    response = client.delete(
        f"/catalog/containers/{system_container['id']}",
        headers=headers,
    )
    assert response.status_code == 403

    response = client.post(
        "/catalog/containers",
        json={"name": "", "volume_ml": 0},
        headers=headers,
    )
    assert response.status_code == 422

    response = client.delete("/catalog/containers/9999", headers=headers)
    assert response.status_code == 404


def test_hydration_rejects_invalid_drinks_and_volumes(client: TestClient):
    headers = register_and_login(client)

    response = client.post(
        "/hydration/logs",
        json={"drink_type_id": 9999, "volume_ml": 500},
        headers=headers,
    )
    assert response.status_code == 404

    response = client.post(
        "/hydration/logs",
        json={"drink_type_id": 1, "volume_ml": 0},
        headers=headers,
    )
    assert response.status_code == 422


def test_hydration_calculates_effective_amount_and_returns_today_progress(client: TestClient):
    headers = register_and_login(client)

    response = client.post(
        "/hydration/logs",
        json={
            "drink_type_id": 1,
            "volume_ml": 500,
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["volume_ml"] == 500
    assert response.json()["effective_ml"] == 500.0

    response = client.post(
        "/hydration/logs",
        json={"drink_type_id": 2, "volume_ml": 500},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["effective_ml"] == 400.0

    response = client.get("/hydration/today", headers=headers)
    assert response.status_code == 200
    progress = response.json()
    assert progress["current_effective_ml"] == 900.0
    assert len(progress["logs"]) == 2
    assert progress["total_target_ml"] > 0
    assert progress["progress_percent"] > 0
