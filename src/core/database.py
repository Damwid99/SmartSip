from collections.abc import Generator
from pathlib import Path
from typing import Any

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from src.core.config import settings

if settings.DATABASE_URL.startswith("sqlite"):
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

POSTGRES_INDEXES_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

SQLModel.metadata.naming_convention = POSTGRES_INDEXES_NAMING_CONVENTION

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})


# 3. Włączenie trybu WAL (Write-Ahead Logging) dla współbieżności SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_session() -> Generator[Session]:
    with Session(engine) as session:
        yield session
