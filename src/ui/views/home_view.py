import asyncio
import datetime
from collections.abc import Callable
from typing import Any

import flet as ft

from src.ui.api_client import ApiError, Json
from src.ui.context import AppContext


def _local_time(iso: str) -> str:
    dt = datetime.datetime.fromisoformat(iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.UTC)
    return dt.astimezone().strftime("%H:%M")


def home_view(ctx: AppContext) -> ft.View:
    page = ctx.page
    drinks_by_id: dict[int, Json] = {}

    # --- wskaźnik celu ---
    ring = ft.ProgressRing(
        value=0.0,
        width=170,
        height=170,
        stroke_width=12,
        color=ft.Colors.BLUE_ACCENT,
        bgcolor=ft.Colors.BLUE_50,
    )
    progress_text = ft.Text("0 / 0 ml", size=18, weight=ft.FontWeight.BOLD)
    percent_text = ft.Text("0%", size=14, color=ft.Colors.GREY_700)
    breakdown_text = ft.Text("", size=12, color=ft.Colors.GREY_600)
    ring_stack = ft.Stack(
        width=170,
        height=170,
        controls=[
            ring,
            ft.Container(
                width=170,
                height=170,
                alignment=ft.Alignment.CENTER,
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.WATER_DROP, color=ft.Colors.BLUE_400, size=28),
                        progress_text,
                        percent_text,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=2,
                ),
            ),
        ],
    )

    drink_dropdown = ft.Dropdown(label="Rodzaj napoju", width=320)
    containers_row = ft.Row(wrap=True, spacing=10, alignment=ft.MainAxisAlignment.CENTER)
    logs_column = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO)

    def selected_drink_id() -> int | None:
        return int(drink_dropdown.value) if drink_dropdown.value else None

    async def add_drink(volume_ml: int) -> None:
        drink_id = selected_drink_id()
        if drink_id is None:
            ctx.notify("Wybierz rodzaj napoju.")
            return
        try:
            await ctx.api.log_drink(drink_type_id=drink_id, volume_ml=volume_ml)
        except ApiError as err:
            ctx.notify(f"Błąd zapisu: {err.detail}")
            return
        name = drinks_by_id[drink_id]["name"]
        ctx.notify(f"Dodano {volume_ml} ml ({name})")
        await refresh()

    def make_quick_add(volume_ml: int) -> Callable[[], Any]:
        async def handler() -> None:
            await add_drink(volume_ml)

        return handler

    def make_delete(log_id: int) -> Callable[[], Any]:
        async def handler() -> None:
            try:
                await ctx.api.delete_log(log_id)
            except ApiError as err:
                ctx.notify(f"Nie udało się usunąć: {err.detail}")
                return
            await refresh()

        return handler

    # --- własna objętość ---
    custom_field = ft.TextField(
        label="Objętość (ml)", keyboard_type=ft.KeyboardType.NUMBER, autofocus=True
    )

    async def confirm_custom() -> None:
        try:
            volume = int((custom_field.value or "").strip())
        except ValueError:
            custom_field.error = "Podaj liczbę całkowitą"
            page.update()
            return
        if not 1 <= volume <= 5000:
            custom_field.error = "Zakres: 1–5000 ml"
            page.update()
            return
        page.pop_dialog()
        await add_drink(volume)

    def cancel_custom() -> None:
        page.pop_dialog()

    custom_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Własna ilość"),
        content=custom_field,
        actions=[
            ft.TextButton("Anuluj", on_click=cancel_custom),
            ft.TextButton("Dodaj", on_click=confirm_custom),
        ],
    )

    def open_custom() -> None:
        custom_field.value = ""
        custom_field.error = None
        page.show_dialog(custom_dialog)

    # --- odświeżanie ---
    async def refresh() -> None:
        try:
            today, containers, drinks = await asyncio.gather(
                ctx.api.today(), ctx.api.containers(), ctx.api.drinks()
            )
        except ApiError as err:
            ctx.notify(f"Błąd odświeżania: {err.detail}")
            return

        drinks_by_id.clear()
        drinks_by_id.update({d["id"]: d for d in drinks})
        if not drink_dropdown.options:
            drink_dropdown.options = [
                ft.DropdownOption(
                    str(d["id"]), f"{d['icon']} {d['name']} (×{d['hydration_multiplier']:g})"
                )
                for d in drinks
            ]
            drink_dropdown.value = str(drinks[0]["id"]) if drinks else None

        current = int(today["current_effective_ml"])
        target = int(today["total_target_ml"])
        ring.value = min(current / target, 1.0) if target > 0 else 0.0
        progress_text.value = f"{current} / {target} ml"
        percent_text.value = f"{today['progress_percent']}% celu"
        breakdown_text.value = (
            f"Baza: {today['base_target_ml']} ml | Pogoda: +{today['weather_bonus_ml']} ml | "
            f"Fit: +{today['activity_bonus_ml']} ml"
        )

        containers_row.controls = [
            ft.Button(
                content=ft.Row(
                    [
                        ft.Text(c.get("icon", "🥛"), size=18),
                        ft.Text(f"{c['name']} ({c['volume_ml']}ml)", size=13),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                on_click=make_quick_add(c["volume_ml"]),
            )
            for c in containers
        ]
        containers_row.controls.append(ft.Button("➕ Własna ilość", on_click=open_custom))

        logs = today.get("logs", [])
        if not logs:
            logs_column.controls = [
                ft.Text(
                    "Brak wpisów dzisiaj. Czas się napić!", italic=True, color=ft.Colors.GREY_500
                )
            ]
        else:
            logs_column.controls = []
            for entry in logs:
                drink = drinks_by_id.get(entry["drink_type_id"], {})
                logs_column.controls.append(
                    ft.Container(
                        padding=ft.Padding(left=8, right=0, top=0, bottom=0),
                        bgcolor=ft.Colors.BLUE_50,
                        border_radius=6,
                        content=ft.Row(
                            [
                                ft.Text(drink.get("icon", "💧"), size=18),
                                ft.Column(
                                    [
                                        ft.Text(
                                            f"{entry['volume_ml']} ml · "
                                            f"{_local_time(entry['created_at'])}",
                                            weight=ft.FontWeight.W_500,
                                        ),
                                        ft.Text(
                                            f"skuteczne: {int(entry['effective_ml'])} ml",
                                            size=12,
                                            color=ft.Colors.GREY_600,
                                        ),
                                    ],
                                    spacing=0,
                                    expand=True,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    tooltip="Usuń wpis",
                                    on_click=make_delete(entry["id"]),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                    )
                )
        page.update()

    async def on_logout() -> None:
        await ctx.sign_out()
        await page.push_route("/login")

    async def on_refresh() -> None:
        await refresh()

    view = ft.View(
        route="/home",
        appbar=ft.AppBar(
            title=ft.Text("SmartSip", weight=ft.FontWeight.BOLD),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            actions=[
                ft.IconButton(icon=ft.Icons.REFRESH, on_click=on_refresh, tooltip="Odśwież"),
                ft.IconButton(icon=ft.Icons.LOGOUT, on_click=on_logout, tooltip="Wyloguj"),
            ],
        ),
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Container(
                padding=16,
                alignment=ft.Alignment.TOP_CENTER,
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ring_stack,
                        breakdown_text,
                        ft.Divider(height=10, color="transparent"),
                        ft.Text("Szybkie dodawanie:", size=16, weight=ft.FontWeight.BOLD),
                        drink_dropdown,
                        containers_row,
                        ft.Divider(height=10, color="transparent"),
                        ft.Text("Dzisiejsze napoje:", size=16, weight=ft.FontWeight.BOLD),
                        ft.Container(content=logs_column, height=260),
                    ],
                ),
            )
        ],
    )

    page.run_task(refresh)
    return view
