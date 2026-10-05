from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship

from src.core.models import Base

if TYPE_CHECKING:
    from src.hydration.models import HydrationLog
    from src.users.models import User


class DrinkType(Base, table=True):
    __tablename__ = "drink_types"
    name: str
    hydration_multiplier: float
    icon: str = Field(default="💧")

    hydration_logs: list["HydrationLog"] = Relationship(back_populates="drink_type")


class Container(Base, table=True):
    __tablename__ = "containers"
    name: str
    volume_ml: int
    icon: str = Field(default="🥛")

    user_id: int | None = Field(default=None, foreign_key="users.id")

    user: Optional["User"] = Relationship(back_populates="containers")  # noqa
