import datetime

from pydantic import BaseModel, ConfigDict, Field


class HydrationLogCreate(BaseModel):
    drink_type_id: int
    volume_ml: int = Field(gt=0, description="Objętość w ml, musi być większa od 0")
    timestamp: datetime.datetime | None = Field(
        default=None, description="Opcjonalny czas spożycia; domyślnie czas rejestru"
    )


class HydrationLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    drink_type_id: int
    volume_ml: int
    effective_ml: float
    created_at: datetime.datetime


class DailyProgressRead(BaseModel):
    date: datetime.date
    base_target_ml: int
    weather_bonus_ml: int
    activity_bonus_ml: int
    total_target_ml: int
    current_effective_ml: float
    progress_percent: float
    logs: list[HydrationLogRead]
