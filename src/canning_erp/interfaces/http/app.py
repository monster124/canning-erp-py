"""Application factory for the HTTP interface (composition root)."""

from fastapi import FastAPI

from canning_erp.interfaces.http.health import router as health_router


def create_app() -> FastAPI:
    """Create the FastAPI application.

    Later stages plug middleware (request-id, auth, rate-limit, ...) and
    domain routers into this factory.
    """
    app = FastAPI(title="Canning ERP", version="0.1.0")
    app.include_router(health_router)
    return app
