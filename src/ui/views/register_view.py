import datetime

import flet as ft

from src.core.config import settings
from src.ui.api_client import ApiError
from src.ui.context import AppContext


def register_view(ctx: AppContext) -> ft.View:
    page = ctx.page
    today = datetime.date.today()
    latest_birth = datetime.date(
        today.year - settings.MIN_ADULT_AGE, today.month, min(today.day, 28)
    )
    birth_date: datetime.date | None = None

    username_input = ft.TextField(label="Nazwa użytkownika", width=300)
    gender_dropdown = ft.Dropdown(
        label="Płeć",
        options=[ft.DropdownOption("male", "Mężczyzna"), ft.DropdownOption("female", "Kobieta")],
        value="male",
        width=300,
    )
    weight_input = ft.TextField(
        label="Waga (kg)", value="75", width=300, keyboard_type=ft.KeyboardType.NUMBER
    )
    location_input = ft.TextField(label="Miasto (do pogody)", value="Warszawa", width=300)
    birth_btn = ft.Button("📅 Wybierz datę urodzenia", width=300)
    error_text = ft.Text(color=ft.Colors.RED, visible=False)

    def on_birth_change() -> None:
        nonlocal birth_date
        value = date_picker.value
        if value:
            birth_date = value.date() if isinstance(value, datetime.datetime) else value
            birth_btn.content = f"📅 {birth_date.strftime('%d.%m.%Y')}"
            page.update()

    date_picker = ft.DatePicker(
        first_date=datetime.datetime(1920, 1, 1),
        last_date=datetime.datetime.combine(latest_birth, datetime.time.min),
        on_change=on_birth_change,
    )
    birth_btn.on_click = lambda: page.show_dialog(date_picker)

    def show_error(message: str) -> None:
        error_text.value = message
        error_text.visible = True
        page.update()

    async def on_submit() -> None:
        error_text.visible = False
        if ctx.pending_credential is None:
            await page.push_route("/login")
            return
        if birth_date is None:
            show_error("Wybierz datę urodzenia.")
            return
        try:
            weight = float((weight_input.value or "").replace(",", "."))
        except ValueError:
            show_error("Podaj poprawną wagę.")
            return

        payload = {
            **ctx.pending_credential,
            "profile": {
                "username": (username_input.value or "").strip(),
                "gender": gender_dropdown.value,
                "weight_kg": weight,
                "birth_date": birth_date.isoformat(),
                "location": (location_input.value or "").strip() or "Warszawa",
            },
        }
        try:
            data = await ctx.api.register_google(payload)
        except ApiError as err:
            show_error(f"Błąd rejestracji: {err.detail}")
            return
        await ctx.sign_in(data["access_token"])
        await page.push_route("/home")

    async def on_cancel() -> None:
        ctx.pending_credential = None
        await page.push_route("/login")

    return ft.View(
        route="/register",
        controls=[
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("Uzupełnij swój profil", size=24, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            "Dane posłużą do precyzyjnego wyliczenia nawodnienia",
                            size=13,
                            color=ft.Colors.GREY_600,
                        ),
                        username_input,
                        gender_dropdown,
                        weight_input,
                        birth_btn,
                        location_input,
                        error_text,
                        ft.Button(
                            "Rozpocznij korzystanie",
                            on_click=on_submit,
                            width=300,
                            bgcolor=ft.Colors.BLUE,
                            color=ft.Colors.WHITE,
                        ),
                        ft.TextButton("Anuluj", on_click=on_cancel),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=12,
                ),
                alignment=ft.Alignment.CENTER,
                expand=True,
            )
        ],
    )
