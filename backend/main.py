import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import load_settings
from backend.database import create_tables, init_db
from backend.hardware import probe_hardware
from backend.logging_config import TraceIDMiddleware, configure_logging
from backend.routers import audit, datasets, deployments, fingerprinting, ingestion, training, validation

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = load_settings(os.environ.get("CONFIG_PATH", "config.toml"))
    configure_logging(settings.log_level)

    app = FastAPI(
        title="RT Auto-Contouring Pipeline",
        description="End-to-end radiotherapy auto-contouring platform API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(TraceIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(ingestion.router, prefix="/api", tags=["Ingestion"])
    app.include_router(datasets.router, prefix="/api", tags=["Datasets"])
    app.include_router(fingerprinting.router, prefix="/api", tags=["Fingerprinting & Guardrails"])
    app.include_router(training.router, prefix="/api", tags=["Training"])
    app.include_router(validation.router, prefix="/api", tags=["Validation"])
    app.include_router(deployments.router, prefix="/api", tags=["Deployments"])
    app.include_router(audit.router, prefix="/api", tags=["Audit"])

    @app.on_event("startup")
    async def on_startup() -> None:
        init_db(settings.database_url)
        await create_tables()
        hw = probe_hardware()
        logger.info("Application started", extra={"hardware": hw})

    @app.get("/health", tags=["Health"])
    async def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
