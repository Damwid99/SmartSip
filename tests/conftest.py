import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from src.catalog.models import Container, DrinkType
from src.core.database import get_session
from src.main import app


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(DrinkType(name="Woda", hydration_multiplier=1.0, icon="💧"))
        session.add(DrinkType(name="Kawa", hydration_multiplier=0.8, icon="☕"))
        session.add(Container(name="Kubek systemowy", volume_ml=250, icon="🥛"))
        session.commit()
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_google_token_verification(monkeypatch: pytest.MonkeyPatch):
    def verify(token: str) -> dict[str, object]:
        return {"sub": token, "email": f"{token}@example.com"}

    monkeypatch.setattr("src.users.router.verify_google_token", verify)
