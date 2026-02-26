from __future__ import annotations

from app.core.config import get_settings

settings = get_settings()

# JWT stub — expanded in Phase 6 with full auth
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7
