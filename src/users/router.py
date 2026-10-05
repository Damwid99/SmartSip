from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from src.core.database import get_session
from src.core.security import (
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from src.users.models import Profile, User
from src.users.schemas import ProfileRead, ProfileUpdate, Token, UserCreate, UserRead

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[Session, Depends(get_session)],
) -> Token:
    user = session.exec(select(User).where(User.email == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Niepoprawny email lub hasło",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Konto użytkownika jest nieaktywne",
        )

    assert user.id is not None
    access_token = create_access_token(subject=user.id)
    return Token(access_token=access_token, token_type="bearer")


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(
    payload: UserCreate,
    session: Annotated[Session, Depends(get_session)],
) -> User:
    if session.exec(select(User).where(User.email == payload.email)).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Użytkownik o takim adresie email już istnieje",
        )

    if session.exec(select(Profile).where(Profile.username == payload.profile.username)).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nazwa użytkownika (username) jest już zajęta",
        )

    # Bezpieczne hashowanie hasła Argon2
    hashed_pwd = get_password_hash(payload.password)
    user = User(
        email=payload.email,
        hashed_password=hashed_pwd,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    assert user.id is not None
    profile = Profile(
        user_id=user.id,
        username=payload.profile.username,
        gender=payload.profile.gender,
        weight_kg=payload.profile.weight_kg,
        birth_date=payload.profile.birth_date,
        location=payload.profile.location,
        google_fit_token=payload.profile.google_fit_token,
    )
    session.add(profile)
    session.commit()
    session.refresh(user)

    return user


@router.get("/me", response_model=UserRead)
def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    return current_user


@router.patch("/me/profile", response_model=ProfileRead)
def update_current_user_profile(
    payload: ProfileUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Profile:
    profile = session.exec(select(Profile).where(Profile.user_id == current_user.id)).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil nie istnieje")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)

    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile
