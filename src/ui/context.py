from dataclasses import dataclass

import flet as ft

from src.ui.api_client import ApiClient
from src.ui.session import SessionStore


@dataclass
class AppContext:
    page: ft.Page
    api: ApiClient
    session: SessionStore
    # dane Google między ekranem logowania a rejestracją
    pending_credential: dict[str, str] | None = None

    async def sign_in(self, token: str) -> None:
        self.api.set_token(token)
        await self.session.save_token(token)
        self.pending_credential = None

    async def sign_out(self) -> None:
        self.api.set_token(None)
        self.pending_credential = None
        await self.session.clear()

    def notify(self, message: str) -> None:
        self.page.show_dialog(ft.SnackBar(ft.Text(message)))
