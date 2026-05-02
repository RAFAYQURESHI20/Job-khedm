"""
backend/api/main.py
-------------------
FastAPI application entry-point for the JobPulse API.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from backend.api.routes import jobs, stats, health


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    # Startup
    import logging
    logging.getLogger(__name__).info("JobPulse API starting up…")
    yield
    # Shutdown
    logging.getLogger(__name__).info("JobPulse API shutting down.")


app = FastAPI(
    title="JobPulse API",
    version=settings.APP_VERSION,
    description="Job aggregation and classification platform API.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["Health"])
app.include_router(jobs.router, prefix=settings.API_V1_PREFIX, tags=["Jobs"])
app.include_router(stats.router, prefix=settings.API_V1_PREFIX, tags=["Stats"])


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
