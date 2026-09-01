"""FastAPI application entry point."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.cache import close_keystore
from app.core.config import settings
from app.core.db import dispose_engine, init_models
from app.core.errors import RevynError
from app.core.logging import configure_logging, get_logger
from app.integrations.llm import reset_reasoner
from app.integrations.razorpay import reset_gateway
from app.workers.scheduler import scheduler

log = get_logger(__name__)

DESCRIPTION = """
Revyn is an AI decision and orchestration layer for revenue recovery.

It detects revenue at risk, diagnoses the cause, predicts recovery probability, selects the
intervention with the highest risk-adjusted incremental value, gates it against a
deterministic policy engine, executes it, verifies the outcome and learns from the result.
"""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    await init_models()
    log.info(
        "app.startup",
        extra={
            "environment": settings.env,
            "gateway": settings.gateway,
            "database": settings.is_sqlite,
        },
    )
    if settings.scheduler_enabled:
        await scheduler.start()
    try:
        yield
    finally:
        await scheduler.stop()
        await reset_gateway()
        await reset_reasoner()
        await close_keystore()
        await dispose_engine()
        log.info("app.shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Revyn",
        summary="AI revenue recovery and autonomous revenue protection platform",
        description=DESCRIPTION,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.exception_handler(RevynError)
    async def handle_domain_error(request: Request, exc: RevynError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.code, "message": exc.message, "details": exc.details},
        )

    @app.get("/", include_in_schema=False)
    async def root() -> dict:
        return {
            "name": "Revyn",
            "version": app.version,
            "docs": "/docs",
            "api": settings.api_prefix,
        }

    return app


app = create_app()
