import flet as ft
from flet.auth.providers import GoogleOAuthProvider

from src.core.config import settings
from src.ui.api_client import ApiError
from src.ui.context import AppContext

GOOGLE_SCOPES = ["openid", "email", "profile"]


def login_view(ctx: AppContext) -> ft.View:
    page = ctx.page
    status_text = ft.Text(color=ft.Colors.RED, visible=False)
    busy = ft.ProgressRing(visible=False, width=24, height=24)

    def show_error(message: str) -> None:
        status_text.value = message
        status_text.visible = True
        page.update()

    def set_busy(value: bool) -> None:
        busy.visible = value
        google_btn.disabled = value
        page.update()

    async def finish_login(token: str) -> None:
        await ctx.sign_in(token)
        await page.push_route("/home")

    async def on_login(e: ft.LoginEvent) -> None:
        if e.error:
            show_error(e.error_description or "Logowanie Google nie powiodło się.")
            set_busy(False)
            return

        try:
            auth = page.auth
            if auth is None:
                show_error("Logowanie Google nie zwróciło sesji.")
                return

            token = await auth.get_token()
            access_token = token.access_token if token else None
            if not access_token:
                show_error("Logowanie Google nie zwróciło tokenu dostępu.")
                return

            credential = {"access_token": access_token}
            try:
                data = await ctx.api.auth_google(credential)
            except ApiError as err:
                if err.status_code == 401 and "nie jest zarejestrowany" in err.detail:
                    ctx.pending_credential = credential
                    await page.push_route("/register")
                    return
                show_error(f"Błąd logowania: {err.detail}")
                return
            await finish_login(data["access_token"])
        except Exception as exc:
            show_error(f"Błąd logowania Google: {exc}")
        finally:
            set_busy(False)

    async def on_google_click() -> None:
        status_text.visible = False
        set_busy(True)
        try:
            provider = GoogleOAuthProvider(
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                redirect_url=settings.GOOGLE_REDIRECT_URL,
            )

            await page.login(provider, fetch_user=False, scope=GOOGLE_SCOPES)
        except Exception as exc:
            show_error(f"Błąd logowania Google: {exc}")
            set_busy(False)
            return
        google_btn.disabled = False
        page.update()

    async def on_dev_login_click() -> None:
        try:
            data = await ctx.api.auth_dev()
        except ApiError as err:
            show_error(f"Dev login: {err.detail}")
            return
        await finish_login(data["access_token"])

    google_btn = ft.Button(
        content=ft.Row(
            [
                ft.Text("G", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.RED),
                ft.Text("Zaloguj przez Google", size=15),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        width=280,
        height=48,
        on_click=on_google_click,
    )
    page.on_login = on_login

    return ft.View(
        route="/login",
        controls=[
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "💧 SmartSip",
                            size=36,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_700,
                        ),
                        ft.Text(
                            "Inteligentne nawodnienie zintegrowane z Google Fit",
                            size=14,
                            color=ft.Colors.GREY_600,
                        ),
                        ft.Divider(height=20, color="transparent"),
                        google_btn,
                        busy,
                        status_text,
                        ft.Divider(height=20, color="transparent"),
                        ft.Button(
                            "⚡ Zaloguj jako Dev (Baza ID=1)",
                            on_click=on_dev_login_click,
                            width=280,
                            visible=settings.DEV_LOGIN_ENABLED,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                alignment=ft.Alignment.CENTER,
                expand=True,
            )
        ],
    )
