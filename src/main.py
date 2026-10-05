from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from src.catalog.router import router as catalog_router
from src.core.config import settings
from src.hydration.router import router as hydration_router
from src.users.router import router as users_router

app = FastAPI(title=settings.PROJECT_NAME)

# Rejestracja modułów
app.include_router(users_router)
app.include_router(catalog_router)
app.include_router(hydration_router)


@app.get("/", include_in_schema=False)
def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
