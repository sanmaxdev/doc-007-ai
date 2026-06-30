"""FastAPI application factory.

Run: `uvicorn doc007.main:app --reload`
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from doc007 import __version__
from doc007.api.v1.router import api_router
from doc007.api.v1.routers import health, public
from doc007.core.config import settings
from doc007.core.exceptions import AppError
from doc007.core.logging import configure_logging, get_logger

log = get_logger(__name__)

_DEV_ENVS = {"development", "dev", "local", "test", "testing"}


def _check_production_safety() -> None:
    """Refuse to boot with insecure defaults outside development."""
    if settings.environment.lower() in _DEV_ENVS:
        return
    if settings.jwt_secret_key in {"", "change-me"} or len(settings.jwt_secret_key) < 32:
        raise RuntimeError(
            "JWT_SECRET_KEY must be set to a strong value (at least 32 characters) "
            "when ENVIRONMENT is not a development environment."
        )
    if settings.debug:
        raise RuntimeError("DEBUG must be disabled outside development.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    _check_production_safety()
    log.info("startup", app=settings.app_name, environment=settings.environment)
    yield
    log.info("shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="Multi-tenant RAG knowledge base API.",
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def _app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "code": exc.code},
        )

    @app.exception_handler(Exception)
    async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        # Log the real error server-side; never leak internals to the client.
        log.error("unhandled_exception", path=request.url.path, error=str(exc))
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error.", "code": "internal_error"},
        )

    # Root-level probes (used by Docker/k8s healthchecks)
    app.include_router(health.router)

    # Versioned business API (JWT-authenticated)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    # Public API (API-key authenticated, rate-limited)
    app.include_router(public.router, prefix="/api/public/v1", tags=["public"])

    @app.get("/", include_in_schema=False)
    async def root() -> dict:
        return {
            "name": settings.app_name,
            "version": __version__,
            "docs": "/docs",
            "health": "/healthz",
        }

    return app


app = create_app()
