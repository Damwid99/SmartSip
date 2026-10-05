import datetime

from pydantic import BaseModel, ConfigDict, Field


class DrinkTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    hydration_multiplier: float
    icon: str
    created_at: datetime.datetime


class ContainerBase(BaseModel):
    name: str = Field(min_length=1, max_length=50, description="Nazwa np. Ulubiony kubek")
    volume_ml: int = Field(gt=0, le=5000, description="Pojemność w ml (maks. 5 litrów)")
    icon: str = Field(default="🥛", max_length=10)


class ContainerCreate(ContainerBase):
    pass


class ContainerRead(ContainerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None = None
    is_custom: bool = False
    created_at: datetime.datetime
