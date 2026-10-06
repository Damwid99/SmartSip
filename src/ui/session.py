import flet as ft

TOKEN_KEY = "smartsip.access_token"


class SessionStore:
    """Trwałe przechowywanie tokenu (SharedPreferences: web, desktop i Android)."""

    def __init__(self, page: ft.Page) -> None:
        self._prefs = ft.SharedPreferences()
        page.services.append(self._prefs)

    async def load_token(self) -> str | None:
        value = await self._prefs.get(TOKEN_KEY)
        return value if isinstance(value, str) and value else None

    async def save_token(self, token: str) -> None:
        await self._prefs.set(TOKEN_KEY, token)

    async def clear(self) -> None:
        await self._prefs.remove(TOKEN_KEY)
