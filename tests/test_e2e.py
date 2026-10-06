from fastapi.testclient import TestClient


def test_full_user_journey_e2e(client: TestClient):
    # 1. Rejestracja nowego użytkownika
    register_payload = {
        "email": "test@example.com",  # Używamy standardowej domeny
        "google_id": "google-test@example.com",
        "profile": {
            "username": "tester",
            "gender": "male",
            "weight_kg": 80.0,
            "birth_date": "1995-01-01",
            "location": "Warszawa",
        },
    }
    response = client.post("/users", json=register_payload)
    # Wypisze dokładny powód błędu, jeśli Pydantic znów coś odrzuci
    assert response.status_code == 201, response.text

    user_data = response.json()
    assert user_data["email"] == "test@example.com"

    # 2. Logowanie przez Google i pobranie tokena JWT
    response = client.post(
        "/users/auth/google",
        json={"id_token": "google-test@example.com"},
    )
    assert response.status_code == 200, response.text

    token_data = response.json()
    assert "access_token" in token_data

    headers = {"Authorization": f"Bearer {token_data['access_token']}"}

    response = client.get("/users/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["profile"]["username"] == "tester"

    response = client.get("/catalog/drinks")
    assert response.status_code == 200
    drinks = response.json()
    assert len(drinks) >= 2
    woda_id = next(d["id"] for d in drinks if d["name"] == "Woda")

    container_payload = {"name": "Mój gigantyczny kubek", "volume_ml": 800, "icon": "🍺"}
    response = client.post("/catalog/containers", json=container_payload, headers=headers)
    assert response.status_code == 201
    assert response.json()["is_custom"] is True

    log_payload = {"drink_type_id": woda_id, "volume_ml": 500}
    response = client.post("/hydration/logs", json=log_payload, headers=headers)
    assert response.status_code == 201
    log_data = response.json()
    assert log_data["effective_ml"] == 500.0

    response = client.get("/hydration/today", headers=headers)
    assert response.status_code == 200
    progress = response.json()

    assert progress["current_effective_ml"] == 500.0
    assert len(progress["logs"]) == 1
    assert progress["logs"][0]["volume_ml"] == 500
    assert progress["total_target_ml"] > 2000
    assert progress["progress_percent"] > 0.0
