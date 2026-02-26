from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from app.utils.aws_client_factory import get_boto3_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settings", tags=["settings"])

from app.core.config import get_settings as _get_app_settings

_ENV_FILE = Path(__file__).resolve().parents[4] / ".env"


def _persist_to_env(key_id: str, secret: str, region: str, scan_regions: list[str], mock: bool) -> None:
    """Write credentials into .env so they survive backend restarts."""
    updates = {
        "MOCK_AWS": "false" if not mock else "true",
        "AWS_ACCESS_KEY_ID": key_id,
        "AWS_SECRET_ACCESS_KEY": secret,
        "AWS_REGION": region,
        "SCAN_REGIONS": ",".join(scan_regions),
    }
    try:
        text = _ENV_FILE.read_text(encoding="utf-8") if _ENV_FILE.exists() else ""
        for k, v in updates.items():
            pattern = rf"^{k}=.*$"
            replacement = f"{k}={v}"
            if re.search(pattern, text, re.MULTILINE):
                text = re.sub(pattern, replacement, text, flags=re.MULTILINE)
            else:
                text = text.rstrip("\n") + f"\n{replacement}\n"
        _ENV_FILE.write_text(text, encoding="utf-8")
        logger.info("Credentials persisted to .env")
    except Exception as e:
        logger.warning(f"Could not write .env: {e}")


def _init_config() -> dict:
    """Seed runtime config from .env via config.py so restarts don't reset to us-east-1."""
    cfg = _get_app_settings()
    return {
        "mock_aws": cfg.mock_aws,
        "aws_access_key_id": cfg.aws_access_key_id or None,
        "aws_secret_access_key": cfg.aws_secret_access_key or None,
        "aws_region": cfg.aws_default_region,
        "scan_regions": cfg.scan_regions_list,
    }

# In-memory store for this session (survives hot-reload, resets on restart)
_current_config: dict = _init_config()



class AWSCredentials(BaseModel):
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str = "us-east-1"
    scan_regions: list[str] = ["us-east-1"]

    @field_validator("aws_access_key_id")
    @classmethod
    def key_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Access key ID cannot be empty")
        return v.strip()

    @field_validator("aws_secret_access_key")
    @classmethod
    def secret_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Secret access key cannot be empty")
        return v.strip()


class SettingsResponse(BaseModel):
    mock_aws: bool
    aws_region: Optional[str]
    scan_regions: list[str]
    aws_access_key_id_hint: Optional[str]   # first 4 + masked, never full key
    connected: bool


def _mask_key(key: str | None) -> str | None:
    if not key:
        return None
    return key[:4] + "****" + key[-4:]


def _test_connection(key_id: str, secret: str, region: str) -> tuple[bool, str]:
    """Try sts:GetCallerIdentity — the lightest possible AWS API call."""
    try:
        import boto3
        session = boto3.Session(
            aws_access_key_id=key_id,
            aws_secret_access_key=secret,
            region_name=region,
        )
        sts = session.client("sts")
        identity = sts.get_caller_identity()
        account = identity.get("Account", "unknown")
        arn = identity.get("Arn", "unknown")
        return True, f"Connected — Account: {account} | Identity: {arn}"
    except Exception as e:
        return False, str(e)


@router.get("", response_model=SettingsResponse)
async def get_settings_endpoint() -> SettingsResponse:
    """Return current configuration (credentials masked)."""
    return SettingsResponse(
        mock_aws=_current_config["mock_aws"],
        aws_region=_current_config.get("aws_region"),
        scan_regions=_current_config.get("scan_regions", ["us-east-1"]),
        aws_access_key_id_hint=_mask_key(_current_config.get("aws_access_key_id")),
        connected=not _current_config["mock_aws"] and bool(_current_config.get("aws_access_key_id")),
    )


@router.post("/aws-credentials")
async def save_aws_credentials(payload: AWSCredentials) -> dict[str, Any]:
    """
    Save AWS credentials and validate them by calling sts:GetCallerIdentity.
    Credentials are held in memory for the current server session.
    """
    ok, message = _test_connection(
        payload.aws_access_key_id,
        payload.aws_secret_access_key,
        payload.aws_region,
    )

    if not ok:
        raise HTTPException(
            status_code=400,
            detail=f"AWS credentials validation failed: {message}",
        )

    # Persist in memory and in .env file so credentials survive restarts
    import os
    was_mock = _current_config["mock_aws"]
    _current_config.update({
        "mock_aws": False,
        "aws_access_key_id": payload.aws_access_key_id,
        "aws_secret_access_key": payload.aws_secret_access_key,
        "aws_region": payload.aws_region,
        "scan_regions": payload.scan_regions,
    })
    os.environ["AWS_ACCESS_KEY_ID"] = payload.aws_access_key_id
    os.environ["AWS_SECRET_ACCESS_KEY"] = payload.aws_secret_access_key
    os.environ["AWS_DEFAULT_REGION"] = payload.aws_region
    os.environ["MOCK_AWS"] = "false"

    # Write to .env so credentials survive backend restarts
    _persist_to_env(
        payload.aws_access_key_id,
        payload.aws_secret_access_key,
        payload.aws_region,
        payload.scan_regions,
        mock=False,
    )

    # Clear stale mock scan data when switching from mock to real mode
    if was_mock:
        from app.core import store
        store.clear_all()
        logger.info("Cleared mock scan data — switched to real AWS mode")

    logger.info("AWS credentials updated via Settings API", extra={"region": payload.aws_region})

    return {
        "success": True,
        "message": message,
        "aws_region": payload.aws_region,
        "scan_regions": payload.scan_regions,
        "key_hint": _mask_key(payload.aws_access_key_id),
    }


@router.post("/use-mock")
async def switch_to_mock() -> dict[str, str]:
    """Switch back to mock mode (useful for demos)."""
    import os
    _current_config.update({
        "mock_aws": True,
        "aws_access_key_id": None,
        "aws_secret_access_key": None,
    })
    os.environ["MOCK_AWS"] = "true"
    os.environ.pop("AWS_ACCESS_KEY_ID", None)
    os.environ.pop("AWS_SECRET_ACCESS_KEY", None)
    return {"success": "true", "mode": "mock"}


@router.get("/scan-regions")
async def get_scan_regions() -> dict[str, list[str]]:
    """Return configured scan regions."""
    return {"scan_regions": _current_config.get("scan_regions", ["us-east-1"])}
