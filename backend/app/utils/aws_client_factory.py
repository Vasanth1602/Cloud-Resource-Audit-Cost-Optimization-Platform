from __future__ import annotations

import logging
from typing import Any

import boto3
from botocore.config import Config

from app.core.config import get_settings

logger = logging.getLogger(__name__)


# Retry configuration for all boto3 clients
_BOTO_RETRY_CONFIG = Config(
    retries={"max_attempts": 3, "mode": "adaptive"},
    connect_timeout=10,
    read_timeout=30,
)


def get_boto3_session(region: str | None = None) -> boto3.Session:
    """
    Build a boto3 session using the configured credential chain.
    Reads settings fresh on every call so credentials set via the
    Settings UI are immediately picked up without a restart.
    """
    settings = get_settings()   # ← always fresh, no module-level cache
    effective_region = region or settings.aws_default_region
    kwargs: dict[str, Any] = {"region_name": effective_region}

    if settings.aws_access_key_id and settings.aws_secret_access_key:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
        if settings.aws_session_token:
            kwargs["aws_session_token"] = settings.aws_session_token

    session = boto3.Session(**kwargs)

    if settings.aws_role_arn:
        logger.info("Assuming IAM role", extra={"role_arn": settings.aws_role_arn})
        sts = session.client("sts")
        creds = sts.assume_role(
            RoleArn=settings.aws_role_arn,
            RoleSessionName="CloudAuditScanner",
        )["Credentials"]
        session = boto3.Session(
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=effective_region,
        )

    return session


def get_client(service: str, region: str | None = None) -> Any:
    """Get a boto3 client for the given service and region with retry config."""
    session = get_boto3_session(region)
    return session.client(service, config=_BOTO_RETRY_CONFIG)


def get_resource_client(service: str, region: str | None = None) -> Any:
    """Get a boto3 resource client for the given service and region."""
    session = get_boto3_session(region)
    return session.resource(service, region_name=region or settings.aws_default_region)
