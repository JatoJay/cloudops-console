import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.routes.health import router as health_router
from app.api.routes.analysis import progress_router, router as analysis_router
from app.api.routes.clusters import router as clusters_router
from app.api.routes.investigation import router as investigation_router
from app.api.routes.vulnerabilities import router as vulnerabilities_router
from app.api.routes.cluster_agents import router as cluster_agents_router
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging(settings.log_level)
    logger.info("Starting {} in {} mode", settings.app_name, settings.environment)
    yield
    logger.info("Stopping {}", settings.app_name)


app = FastAPI(title="CloudOps Console API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    started_at = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - started_at) * 1000
    logger.info(
        "{} {} -> {} ({:.1f} ms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


app.include_router(health_router)
app.include_router(analysis_router)
app.include_router(progress_router)
app.include_router(clusters_router)
app.include_router(investigation_router)
app.include_router(vulnerabilities_router)
app.include_router(cluster_agents_router)
