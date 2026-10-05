import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, col, select

from src.catalog.models import DrinkType
from src.core.database import get_session
from src.core.security import get_current_user
from src.hydration.models import DailyTarget, HydrationLog
from src.hydration.schemas import DailyProgressRead, HydrationLogCreate, HydrationLogRead
from src.hydration.services import calculate_effective_ml, calculate_total_target_ml
from src.users.models import User

router = APIRouter(prefix="/hydration", tags=["Hydration"])


@router.post("/logs", response_model=HydrationLogRead, status_code=status.HTTP_201_CREATED)
def log_drink(
    payload: HydrationLogCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> HydrationLog:
    assert current_user.id is not None  # Zapewnienie typu dla mypy strict

    drink_type = session.get(DrinkType, payload.drink_type_id)
    if not drink_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wybrany napój nie istnieje w katalogu",
        )

    effective_ml = calculate_effective_ml(
        volume_ml=payload.volume_ml,
        hydration_factor=drink_type.hydration_multiplier,
    )

    log_entry = HydrationLog(
        user_id=current_user.id,
        drink_type_id=payload.drink_type_id,
        volume_ml=payload.volume_ml,
        effective_ml=effective_ml,
    )

    if payload.timestamp:
        log_entry.created_at = payload.timestamp

    session.add(log_entry)
    session.commit()
    session.refresh(log_entry)

    return log_entry


@router.get("/today", response_model=DailyProgressRead)
def get_today_progress(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> DailyProgressRead:
    assert current_user.id is not None

    if not current_user.profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Użytkownik nie posiada uzupełnionego profilu fizycznego",
        )

    today = datetime.date.today()

    target = session.exec(
        select(DailyTarget).where(
            DailyTarget.user_id == current_user.id,
            DailyTarget.date == today,
        )
    ).first()

    if not target:
        # TODO Wartości domyślne do czasu podpięcia pogody i Google Fit
        apparent_temp_c = 20.0
        active_kcal = 0.0

        total_target = calculate_total_target_ml(current_user, apparent_temp_c, active_kcal)
        target = DailyTarget(
            user_id=current_user.id,
            date=today,
            base_target_ml=total_target,
            weather_bonus_ml=0,
            activity_bonus_ml=0,
            total_target_ml=total_target,
        )
        session.add(target)
        session.commit()
        session.refresh(target)

    # 2. Zakres czasowy dla dzisiejszego dnia (UTC)
    today_start = datetime.datetime.combine(today, datetime.time.min, tzinfo=datetime.UTC)
    today_end = datetime.datetime.combine(today, datetime.time.max, tzinfo=datetime.UTC)

    logs = list(
        session.exec(
            select(HydrationLog)
            .where(
                HydrationLog.user_id == current_user.id,
                col(HydrationLog.created_at) >= today_start,
                col(HydrationLog.created_at) <= today_end,
            )
            .order_by(col(HydrationLog.created_at).desc())
        ).all()
    )

    current_effective_ml = sum(entry.effective_ml for entry in logs)
    progress_percent = (
        round((current_effective_ml / target.total_target_ml) * 100, 1)
        if target.total_target_ml > 0
        else 0.0
    )

    return DailyProgressRead(
        date=today,
        base_target_ml=target.base_target_ml,
        weather_bonus_ml=target.weather_bonus_ml,
        activity_bonus_ml=target.activity_bonus_ml,
        total_target_ml=target.total_target_ml,
        current_effective_ml=round(current_effective_ml, 1),
        progress_percent=progress_percent,
        logs=[HydrationLogRead.model_validate(log) for log in logs],
    )
