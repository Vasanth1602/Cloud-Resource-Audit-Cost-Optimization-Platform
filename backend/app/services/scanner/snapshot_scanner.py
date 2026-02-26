"""
EBS Snapshot scanner.
Finds all owned snapshots and flags old ones (>30 days) not linked to an AMI.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.core.config import get_settings
from app.utils.aws_client_factory import get_client

logger = logging.getLogger(__name__)


def _mock_snapshot_resources(region: str) -> list[dict[str, Any]]:
    return [
        {
            "resource_id": "snap-0abc123456",
            "resource_type": "SNAPSHOT",
            "region": region,
            "name": "old-backup",
            "state": "completed",
            "tags": {},
            "raw_data": {
                "size_gb": 50,
                "age_days": 45,
                "ami_id": None,
                "description": "old-backup",
                "start_time": "2024-12-01T00:00:00Z",
            },
        },
    ]


def scan_snapshots(region: str) -> list[dict[str, Any]]:
    settings = get_settings()
    if settings.mock_aws:
        return _mock_snapshot_resources(region)

    client = get_client("ec2", region)
    resources: list[dict[str, Any]] = []

    try:
        # Collect all AMI snapshot IDs so we can flag orphaned snapshots
        ami_snapshot_ids: set[str] = set()
        try:
            ami_resp = client.describe_images(Owners=["self"])
            for image in ami_resp.get("Images", []):
                for mapping in image.get("BlockDeviceMappings", []):
                    snap = mapping.get("Ebs", {}).get("SnapshotId")
                    if snap:
                        ami_snapshot_ids.add(snap)
        except Exception:
            pass

        paginator = client.get_paginator("describe_snapshots")
        now = datetime.now(timezone.utc)
        for page in paginator.paginate(OwnerIds=["self"]):
            for snap in page.get("Snapshots", []):
                tags = {t["Key"]: t["Value"] for t in snap.get("Tags", [])}
                start_time = snap.get("StartTime")
                age_days = int((now - start_time).days) if start_time else 0
                snap_id = snap["SnapshotId"]
                ami_id = snap_id if snap_id in ami_snapshot_ids else None
                resources.append({
                    "resource_id": snap_id,
                    "resource_type": "SNAPSHOT",
                    "region": region,
                    "name": tags.get("Name", snap.get("Description", "")),
                    "state": snap.get("State", "completed"),
                    "tags": tags,
                    "raw_data": {
                        "size_gb": snap.get("VolumeSize", 0),
                        "age_days": age_days,
                        "ami_id": ami_id,
                        "description": snap.get("Description", ""),
                        "start_time": start_time.isoformat() if start_time else None,
                    },
                })
    except Exception as e:
        logger.error(f"Snapshot scan failed in {region}: {e}")

    return resources
