import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship

from src.core.models import Base

if TYPE_CHECKING:
    from src.catalog.models import Container
    from src.hydration.models import DailyTarget, HydrationLog


class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"


class User(Base, table=True):
    __tablename__ = "users"
    email: str = Field(unique=True, index=True)
    google_id: str = Field(unique=True, index=True)
    is_active: bool = Field(default=True)

    profile: Optional["Profile"] = Relationship(  # noqa
        back_populates="user",
        sa_relationship_kwargs={
            "uselist": False,
            "cascade": "all, delete-orphan",
        },
    )

    containers: list["Container"] = Relationship(back_populates="user")
    hydration_logs: list["HydrationLog"] = Relationship(back_populates="user")
    daily_targets: list["DailyTarget"] = Relationship(back_populates="user")


class Profile(Base, table=True):
    __tablename__ = "profiles"
    user_id: int = Field(foreign_key="users.id", unique=True, index=True)

    username: str = Field(unique=True, index=True)
    gender: Gender
    weight_kg: float
    birth_date: datetime.date
    location: str
    google_fit_token: str | None = Field(default=None)

    user: User = Relationship(back_populates="profile")
