"""
EIP (Elastic IP) scanner.
Scans all allocated Elastic IPs in a region and flags unassociated ones.
"""
from __future__ import annotations

import logging
from typing import Any

from app.core.config import get_settings
from app.utils.aws_client_factory import get_client

logger = logging.getLogger(__name__)


def _mock_eip_resources(region: str) -> list[dict[str, Any]]:
    return [
        {
            "resource_id": "54.210.100.1",
            "resource_type": "EIP",
            "region": region,
            "name": None,
            "state": "unassociated",
            "tags": {},
            "raw_data": {
                "allocation_id": "eipalloc-0abc123",
                "associated": False,
                "association_id": None,
                "instance_id": None,
                "domain": "vpc",
            },
        },
    ]


def scan_eip(region: str) -> list[dict[str, Any]]:
    settings = get_settings()
    if settings.mock_aws:
        return _mock_eip_resources(region)

    client = get_client("ec2", region)
    resources: list[dict[str, Any]] = []

    try:
        resp = client.describe_addresses()
        for addr in resp.get("Addresses", []):
            tags = {t["Key"]: t["Value"] for t in addr.get("Tags", [])}
            associated = bool(addr.get("AssociationId"))
            resources.append({
                "resource_id": addr.get("PublicIp", addr.get("AllocationId", "unknown")),
                "resource_type": "EIP",
                "region": region,
                "name": tags.get("Name"),
                "state": "associated" if associated else "unassociated",
                "tags": tags,
                "raw_data": {
                    "allocation_id": addr.get("AllocationId"),
                    "associated": associated,
                    "association_id": addr.get("AssociationId"),
                    "instance_id": addr.get("InstanceId"),
                    "domain": addr.get("Domain", "vpc"),
                },
            })
    except Exception as e:
        logger.error(f"EIP scan failed in {region}: {e}")

    return resources
