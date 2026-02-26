from __future__ import annotations

import logging
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import get_settings
from app.utils.aws_client_factory import get_client

logger = logging.getLogger(__name__)

_BYTES_PER_GB = 1024 ** 3


def _get_nat_data_transfer_gb(nat_id: str, region: str, period_days: int = 7) -> float:
    """Fetch total bytes out from NAT Gateway via CloudWatch over the past N days."""
    try:
        cw = get_client("cloudwatch", region)
        end = datetime.now(tz=timezone.utc)
        start = end - timedelta(days=period_days)
        resp = cw.get_metric_statistics(
            Namespace="AWS/NATGateway",
            MetricName="BytesOutToDestination",
            Dimensions=[{"Name": "NatGatewayId", "Value": nat_id}],
            StartTime=start,
            EndTime=end,
            Period=period_days * 86400,
            Statistics=["Sum"],
        )
        points = resp.get("Datapoints", [])
        if points:
            total_bytes = sum(p["Sum"] for p in points)
            return round(total_bytes / _BYTES_PER_GB, 4)
    except Exception as exc:
        logger.debug("CloudWatch BytesOutToDestination for %s failed: %s", nat_id, exc)
    return 0.0


def _mock_nat_resources(region: str) -> list[dict[str, Any]]:
    vpc_ids = [f"vpc-{uuid.uuid4().hex[:8]}" for _ in range(2)]
    resources = []
    for i in range(random.randint(1, 2)):
        data_gb = round(random.uniform(0.05, 200.0), 4)
        resources.append({
            "resource_id": f"nat-{uuid.uuid4().hex[:17]}",
            "resource_type": "NAT",
            "region": region,
            "name": f"nat-gateway-{i + 1:02d}",
            "state": random.choice(["available", "available", "pending"]),
            "tags": {
                "Environment": random.choice(["production", "staging", ""]),
                "Owner": random.choice(["team-platform", ""]),
            },
            "raw_data": {
                "vpc_id": random.choice(vpc_ids),
                "subnet_id": f"subnet-{uuid.uuid4().hex[:8]}",
                "data_transfer_gb": data_gb,
                "connectivity_type": random.choice(["public", "private"]),
                "allocation_id": f"eipalloc-{uuid.uuid4().hex[:17]}",
            },
        })
    return resources


def scan_nat(region: str) -> list[dict[str, Any]]:
    """Scan NAT Gateways in the given region."""
    settings = get_settings()
    if settings.mock_aws:
        return _mock_nat_resources(region)

    client = get_client("ec2", region)
    resources = []
    paginator = client.get_paginator("describe_nat_gateways")

    for page in paginator.paginate(
        Filters=[{"Name": "state", "Values": ["available", "pending", "deleting"]}]
    ):
        for nat in page.get("NatGateways", []):
            nat_id = nat["NatGatewayId"]
            tags = {t["Key"]: t["Value"] for t in nat.get("Tags", [])}
            name = tags.get("Name", nat_id)

            # Connectivity type: public (has EIP) or private
            addresses = nat.get("NatGatewayAddresses", [])
            allocation_id = addresses[0].get("AllocationId") if addresses else None
            connectivity_type = nat.get("ConnectivityType", "public")

            data_gb = _get_nat_data_transfer_gb(nat_id, region)

            resources.append({
                "resource_id": nat_id,
                "resource_type": "NAT",
                "region": region,
                "name": name,
                "state": nat.get("State"),
                "tags": tags,
                "raw_data": {
                    "vpc_id": nat.get("VpcId"),
                    "subnet_id": nat.get("SubnetId"),
                    "data_transfer_gb": data_gb,
                    "connectivity_type": connectivity_type,
                    "allocation_id": allocation_id,
                },
            })

    return resources
