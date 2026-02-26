from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: str = "development"
    app_port: int = 8000
    app_version: str = "1.0.0"
    secret_key: str = "dev-secret-key-change-in-production"
    debug: bool = True

    # AWS
    mock_aws: bool = True
    aws_default_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_session_token: str = ""
    aws_role_arn: str = ""

    # Scanner
    scan_regions: str = "us-east-1,us-west-2"

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    @property
    def scan_regions_list(self) -> List[str]:
        return [r.strip() for r in self.scan_regions.split(",") if r.strip()]

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


def get_settings() -> Settings:
    return Settings()
