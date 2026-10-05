from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from src.core.config import settings
from src.hydration.router import router as hydration_router

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(hydration_router)


@app.get("/", include_in_schema=False)
def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
