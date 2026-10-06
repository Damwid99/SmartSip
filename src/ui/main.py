import asyncio

import flet as ft

from src.core.config import settings
from src.ui.api_client import ApiClient, ApiError
from src.ui.context import AppContext
from src.ui.session import SessionStore
from src.ui.views.home_view import home_view
from src.ui.views.login_view import login_view
from src.ui.views.register_view import register_view


async def main(page: ft.Page) -> None:
    page.title = "SmartSip - Monitor Nawodnienia"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window.width = 420
    page.window.height = 760

    ctx = AppContext(page=page, api=ApiClient(settings.UI_API_BASE_URL), session=SessionStore(page))
    restoring = True

    async def expire_session() -> None:
        await ctx.sign_out()
        ctx.notify("Sesja wygasła, zaloguj się ponownie.")
        await page.push_route("/login")

    def on_unauthorized() -> None:
        page.run_task(expire_session)

    ctx.api.on_unauthorized = on_unauthorized

    def route_change(e: ft.RouteChangeEvent | None = None) -> None:
        page.views.clear()

        if restoring:
            page.views.append(
                ft.View(
                    route="/",
                    controls=[
                        ft.Container(
                            content=ft.ProgressRing(),
                            alignment=ft.Alignment.CENTER,
                            expand=True,
                        )
                    ],
                )
            )
            page.update()
            return

        route = page.route
        if route in ("", "/"):
            route = "/home" if ctx.api.is_authenticated else "/login"
        if route == "/home" and not ctx.api.is_authenticated:
            route = "/login"
        if route == "/login" and ctx.api.is_authenticated:
            route = "/home"
        if route == "/register" and ctx.pending_credential is None:
            route = "/login"

        if route == "/register":
            page.views.append(register_view(ctx))
        elif route == "/home":
            page.views.append(home_view(ctx))
        else:
            page.views.append(login_view(ctx))
        page.update()

    page.on_route_change = route_change
    route_change()

    async def restore_session() -> None:
        token = await asyncio.wait_for(ctx.session.load_token(), timeout=5)
        if not token:
            return
        ctx.api.set_token(token)
        try:
            await ctx.api.me()
        except ApiError as err:
            if err.status_code != 0:
                await ctx.sign_out()

    try:
        await restore_session()
    except Exception as exc:
        print(f"[SmartSip] Nie udało się przywrócić sesji: {exc!r}")

    restoring = False
    route_change()


if __name__ == "__main__":
    print("SmartSip działa na http://localhost:8002")
    ft.run(main, host="localhost", view=ft.AppView.WEB_BROWSER, port=8002)
