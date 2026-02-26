from __future__ import annotations

import random
import uuid
from typing import Any

from app.core.config import get_settings
from app.utils.aws_client_factory import get_client


def _mock_ebs_resources(region: str) -> list[dict[str, Any]]:
    states = ["in-use", "in-use", "available", "available"]
    volume_types = ["gp2", "gp3", "io1", "st1"]
    resources = []
    for i in range(random.randint(3, 6)):
        state = random.choice(states)
        size_gb = random.choice([20, 50, 100, 200, 500])
        resources.append({
            "resource_id": f"vol-{uuid.uuid4().hex[:16]}",
            "resource_type": "EBS",
            "region": region,
            "name": f"data-volume-{i+1:02d}" if state == "in-use" else None,
            "state": state,
            "tags": {
                "Environment": random.choice(["production", "staging", ""]),
                "Owner": random.choice(["team-platform", ""]),
            },
            "raw_data": {
                "size_gb": size_gb,
                "volume_type": random.choice(volume_types),
                "encrypted": random.choice([True, True, False]),
                "attached_instance": f"i-{uuid.uuid4().hex[:16]}" if state == "in-use" else None,
                "iops": random.randint(100, 3000),
            },
        })
    return resources


def scan_ebs(region: str) -> list[dict[str, Any]]:
    settings = get_settings()
    if settings.mock_aws:
        return _mock_ebs_resources(region)

    client = get_client("ec2", region)
    paginator = client.get_paginator("describe_volumes")
    resources = []

    for page in paginator.paginate():
        for vol in page["Volumes"]:
            name = next(
                (t["Value"] for t in vol.get("Tags", []) if t["Key"] == "Name"),
                None,
            )
            tags = {t["Key"]: t["Value"] for t in vol.get("Tags", [])}
            attachments = vol.get("Attachments", [])
            resources.append({
                "resource_id": vol["VolumeId"],
                "resource_type": "EBS",
                "region": region,
                "name": name,
                "state": vol["State"],
                "tags": tags,
                "raw_data": {
                    "size_gb": vol.get("Size"),
                    "volume_type": vol.get("VolumeType"),
                    "encrypted": vol.get("Encrypted", False),
                    "attached_instance": attachments[0].get("InstanceId") if attachments else None,
                    "iops": vol.get("Iops"),
                },
            })
    return resources
