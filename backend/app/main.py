from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import audit, health
from app.api.routes import settings as settings_route
from app.core.config import get_settings
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(
    title="Cloud Resource Audit Platform",
    description="Multi-region AWS Resource Audit Engine",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

settings = get_settings()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router)
app.include_router(audit.router, prefix="/api/v1")
app.include_router(settings_route.router, prefix="/api/v1")


@app.get("/api/v1/version")
async def version():
    s = get_settings()
    return {"version": "1.0.0", "environment": s.app_env, "mock_aws": s.mock_aws}
