"""ASGI entrypoint."""

from fastapi import FastAPI
from sqlalchemy import text

from app.api.dependencies import SessionDependency
from app.api.error_handlers import register_error_handlers
from app.carts.router import router as carts_router
from app.catalog.router import router as catalog_router


def create_app() -> FastAPI:
    app = FastAPI(title="Checkout and Rewards Service", version="0.1.0")
    register_error_handlers(app)
    app.include_router(catalog_router)
    app.include_router(carts_router)

    @app.get("/health/live", tags=["health"])
    def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready", tags=["health"])
    def ready(session: SessionDependency) -> dict[str, str]:
        session.execute(text("SELECT 1"))
        return {"status": "ok"}

    return app


app = create_app()
