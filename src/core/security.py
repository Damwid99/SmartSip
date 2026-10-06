import datetime
from typing import Annotated, Any

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from sqlmodel import Session

from src.core.config import settings
from src.core.database import get_session
from src.users.models import User

security_scheme = HTTPBearer()
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"


def verify_google_token(token: str) -> dict[str, Any]:
    """Weryfikuje podpisany token tożsamości Google dla tej aplikacji."""
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    claims = id_token.verify_oauth2_token(  # type: ignore[no-untyped-call]
        token,
        google_requests.Request(),
        settings.GOOGLE_CLIENT_ID,
    )
    return {str(key): value for key, value in claims.items()}


def verify_google_access_token(access_token: str) -> dict[str, Any]:
    """Weryfikuje access_token w Google i sprawdza, czy wystawiono go dla TEJ aplikacji."""
    try:
        response = httpx.get(
            GOOGLE_TOKENINFO_URL, params={"access_token": access_token}, timeout=5.0
        )
    except httpx.HTTPError as exc:
        raise ValueError("Nie można zweryfikować tokenu Google") from exc

    if response.status_code != 200:
        raise ValueError("Niepoprawny token Google")

    claims: dict[str, Any] = response.json()
    if claims.get("aud") != settings.GOOGLE_CLIENT_ID:
        raise ValueError("Token Google wystawiony dla innej aplikacji")
    if not claims.get("sub"):
        raise ValueError("Token Google nie zawiera identyfikatora użytkownika")
    return claims


def create_access_token(
    subject: str | int,
    expires_delta: datetime.timedelta | None = None,
) -> str:
    """Tworzy wewnętrzny token dostępowy JWT dla aplikacji SmartSip."""
    now = datetime.datetime.now(datetime.UTC)
    expire = (
        now + expires_delta
        if expires_delta
        else now + datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    to_encode = {
        "exp": expire,
        "iat": now,
        "sub": str(subject),
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security_scheme)],
    session: Annotated[Session, Depends(get_session)],
) -> User:
    """Wyciąga token z nagłówka Authorization, parsuje go i pobiera zalogowanego użytkownika."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Niepoprawne dane uwierzytelniające",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id_raw: str | None = payload.get("sub")
        if user_id_raw is None:
            raise credentials_exception
        user_id = int(user_id_raw)
    except InvalidTokenError, ValueError:
        raise credentials_exception from None

    user = session.get(User, user_id)
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Konto użytkownika jest zablokowane",
        )

    return user
