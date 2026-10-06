from collections.abc import Callable
from typing import Any, cast

import httpx

Json = dict[str, Any]


class ApiError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code  # 0 = brak połączenia
        self.detail = detail


def _extract_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        body = None
    detail = body.get("detail") if isinstance(body, dict) else None
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):  # błędy walidacji 422
        messages: list[str] = []
        for item in detail:
            if not isinstance(item, dict):
                messages.append(str(item))
                continue
            message = str(item.get("msg", item))
            location = item.get("loc")
            if isinstance(location, list) and location:
                field = ".".join(str(part) for part in location if part != "body")
                if field:
                    message = f"{field}: {message}"
            messages.append(message)
        return "; ".join(messages)
    return response.text or f"HTTP {response.status_code}"


class ApiClient:
    def __init__(self, base_url: str) -> None:
        self._http = httpx.AsyncClient(base_url=base_url, timeout=10.0)
        self._token: str | None = None
        self.on_unauthorized: Callable[[], Any] | None = None

    @property
    def is_authenticated(self) -> bool:
        return self._token is not None

    def set_token(self, token: str | None) -> None:
        self._token = token
        if token:
            self._http.headers["Authorization"] = f"Bearer {token}"
        else:
            self._http.headers.pop("Authorization", None)

    async def _request(self, method: str, path: str, json: Any = None) -> httpx.Response:
        try:
            response = await self._http.request(method, path, json=json)
        except httpx.HTTPError as exc:
            raise ApiError(0, f"Brak połączenia z API: {exc}") from exc
        if response.status_code == 401 and self._token and self.on_unauthorized:
            self.on_unauthorized()  # wygasła lub nieważna sesja
        if response.is_error:
            raise ApiError(response.status_code, _extract_detail(response))
        return response

    async def auth_google(self, credential: Json) -> Json:
        return cast(Json, (await self._request("POST", "/users/auth/google", credential)).json())

    async def register_google(self, payload: Json) -> Json:
        r = await self._request("POST", "/users/auth/google/register", payload)
        return cast(Json, r.json())

    async def auth_dev(self) -> Json:
        return cast(Json, (await self._request("POST", "/users/auth/dev")).json())

    async def me(self) -> Json:
        return cast(Json, (await self._request("GET", "/users/me")).json())

    async def today(self) -> Json:
        return cast(Json, (await self._request("GET", "/hydration/today")).json())

    async def containers(self) -> list[Json]:
        return cast(list[Json], (await self._request("GET", "/catalog/containers")).json())

    async def drinks(self) -> list[Json]:
        return cast(list[Json], (await self._request("GET", "/catalog/drinks")).json())

    async def log_drink(self, drink_type_id: int, volume_ml: int) -> Json:
        body = {"drink_type_id": drink_type_id, "volume_ml": volume_ml}
        return cast(Json, (await self._request("POST", "/hydration/logs", body)).json())

    async def delete_log(self, log_id: int) -> None:
        await self._request("DELETE", f"/hydration/logs/{log_id}")
