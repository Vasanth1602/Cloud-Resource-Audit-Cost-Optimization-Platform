from __future__ import annotations

from fastapi import APIRouter

from app.core import store
from app.core.config import get_settings

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health")
async def health():
    return {
        "status": "healthy",
        "mock_aws": settings.mock_aws,
        "scan_count": len(store.scan_sessions),
        "resource_count": sum(len(v) for v in store.scan_resources.values()),
    }
