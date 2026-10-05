import datetime
from typing import TYPE_CHECKING

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship

from src.core.models import Base

if TYPE_CHECKING:
    from src.catalog.models import DrinkType
    from src.users.models import User


class HydrationLog(Base, table=True):
    __tablename__ = "hydration_logs"
    user_id: int = Field(foreign_key="users.id")
    drink_type_id: int = Field(foreign_key="drink_types.id")
    volume_ml: int
    effective_ml: float

    user: "User" = Relationship(back_populates="hydration_logs")
    drink_type: "DrinkType" = Relationship(back_populates="hydration_logs")


class DailyTarget(Base, table=True):
    __tablename__ = "daily_targets"
    __table_args__ = (UniqueConstraint("user_id", "date"),)

    user_id: int = Field(foreign_key="users.id")
    date: datetime.date
    base_target_ml: int
    weather_bonus_ml: int = Field(default=0)
    activity_bonus_ml: int = Field(default=0)
    total_target_ml: int

    user: "User" = Relationship(back_populates="daily_targets")
