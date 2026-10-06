from typing import Any, cast

import httpx

from src.core.config import settings


class AppState:
    def __init__(self) -> None:
        self.api_url: str = settings.UI_API_BASE_URL
        self.access_token: str | None = None
        self.cached_google_id: str | None = None
        self.cached_email: str | None = None
        self.client: httpx.Client = httpx.Client(base_url=self.api_url, timeout=10.0)

    def set_token(self, token: str) -> None:
        self.access_token = token
        self.client.headers.update({"Authorization": f"Bearer {token}"})

    def logout(self) -> None:
        self.access_token = None
        self.cached_email = None
        self.cached_google_id = None
        if "Authorization" in self.client.headers:
            del self.client.headers["Authorization"]

    def auth_google(self, id_token: str) -> httpx.Response:
        return self.client.post("/users/auth/google", json={"id_token": id_token})

    def register(self, payload: dict[str, Any]) -> httpx.Response:
        return self.client.post("/users", json=payload)

    def get_today_progress(self) -> dict[str, Any]:
        response = self.client.get("/hydration/today")
        response.raise_for_status()
        return cast(dict[str, Any], response.json())

    def get_containers(self) -> list[dict[str, Any]]:
        response = self.client.get("/catalog/containers")
        response.raise_for_status()
        return cast(list[dict[str, Any]], response.json())

    def get_drinks(self) -> list[dict[str, Any]]:
        response = self.client.get("/catalog/drinks")
        response.raise_for_status()
        return cast(list[dict[str, Any]], response.json())

    def log_drink(self, drink_type_id: int, volume_ml: int) -> dict[str, Any]:
        response = self.client.post(
            "/hydration/logs", json={"drink_type_id": drink_type_id, "volume_ml": volume_ml}
        )
        response.raise_for_status()
        return cast(dict[str, Any], response.json())


state = AppState()
