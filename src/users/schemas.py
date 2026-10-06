import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from src.users.models import Gender


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: int | None = None


class GoogleAuthRequest(BaseModel):
    id_token: str


class ProfileBase(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    gender: Gender
    weight_kg: float = Field(gt=20.0, lt=300.0, description="Waga w kilogramach")
    birth_date: datetime.date
    location: str = Field(default="Warszawa")
    google_fit_token: str | None = None


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(BaseModel):
    weight_kg: float | None = Field(default=None, gt=20.0, lt=300.0)
    location: str | None = None
    google_fit_token: str | None = None


class ProfileRead(ProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime.datetime


class UserCreate(BaseModel):
    email: EmailStr
    google_id: str
    profile: ProfileCreate


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    google_id: str
    is_active: bool
    created_at: datetime.datetime
    profile: ProfileRead | None = None
