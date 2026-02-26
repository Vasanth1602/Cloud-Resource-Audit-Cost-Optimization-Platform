from __future__ import annotations

import logging
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import get_settings
from app.utils.aws_client_factory import get_client

logger = logging.getLogger(__name__)


def _get_s3_cw_metric(bucket_name: str, region: str, metric_name: str, storage_type: str) -> float:
    """Fetch a CloudWatch S3 metric (BucketSizeBytes or NumberOfObjects) for a bucket.
    Returns 0.0 on failure."""
    try:
        cw = get_client("cloudwatch", region or "us-east-1")
        end = datetime.now(tz=timezone.utc)
        start = end - timedelta(days=3)  # S3 metrics are daily; 3-day window is sufficient
        resp = cw.get_metric_statistics(
            Namespace="AWS/S3",
            MetricName=metric_name,
            Dimensions=[
                {"Name": "BucketName", "Value": bucket_name},
                {"Name": "StorageType", "Value": storage_type},
            ],
            StartTime=start,
            EndTime=end,
            Period=86400,
            Statistics=["Average"],
        )
        points = sorted(resp.get("Datapoints", []), key=lambda p: p["Timestamp"], reverse=True)
        if points:
            return float(points[0]["Average"])
    except Exception as exc:
        logger.debug("CloudWatch metric %s for %s failed: %s", metric_name, bucket_name, exc)
    return 0.0


def _get_s3_size_and_count(bucket_name: str, region: str) -> tuple[float, int]:
    """Return (size_gb, object_count) for a bucket via CloudWatch."""
    size_bytes = _get_s3_cw_metric(bucket_name, region, "BucketSizeBytes", "StandardStorage")
    size_gb = round(size_bytes / (1024 ** 3), 3)
    object_count = int(_get_s3_cw_metric(bucket_name, region, "NumberOfObjects", "AllStorageTypes"))
    return size_gb, object_count


def _get_s3_last_accessed_days(bucket_name: str, region: str) -> int:
    """Estimate days since last access using CloudWatch S3 BucketSizeBytes.
    Returns 0 if we cannot determine (error or no data)."""
    try:
        cw = get_client("cloudwatch", region or "us-east-1")
        end = datetime.now(tz=timezone.utc)
        resp = cw.get_metric_statistics(
            Namespace="AWS/S3",
            MetricName="BucketSizeBytes",
            Dimensions=[
                {"Name": "BucketName", "Value": bucket_name},
                {"Name": "StorageType", "Value": "StandardStorage"},
            ],
            StartTime=end.replace(day=1, hour=0, minute=0, second=0),
            EndTime=end,
            Period=86400,
            Statistics=["Average"],
        )
        points = sorted(resp.get("Datapoints", []), key=lambda p: p["Timestamp"], reverse=True)
        if points:
            last_ts = points[0]["Timestamp"].replace(tzinfo=timezone.utc)
            return max(0, (end - last_ts).days)
    except Exception:
        pass
    return 0


def _mock_s3_resources(region: str) -> list[dict[str, Any]]:
    resources = []
    bucket_names = [
        "app-data-bucket", "logs-archive", "static-assets", "backup-store",
        "ml-datasets", "terraform-state", "media-uploads"
    ]
    for i, bname in enumerate(random.sample(bucket_names, random.randint(2, 4))):
        last_accessed_days = random.randint(0, 120)
        resources.append({
            "resource_id": f"{bname}-{uuid.uuid4().hex[:6]}",
            "resource_type": "S3",
            "region": "us-east-1",  # S3 is global but buckets have a region
            "name": bname,
            "state": "active",
            "tags": {
                "Environment": random.choice(["production", "staging", ""]),
                "Owner": random.choice(["team-platform", ""]),
            },
            "raw_data": {
                "public_access_blocked": random.choice([True, True, False]),
                "versioning_enabled": random.choice([True, False]),
                "encryption_enabled": random.choice([True, True, False]),
                "has_lifecycle_policy": random.choice([True, False]),
                "size_gb": random.randint(1, 5000),
                "object_count": random.randint(100, 1_000_000),
                "last_accessed_days": last_accessed_days,
            },
        })
    return resources


def scan_s3(region: str) -> list[dict[str, Any]]:
    settings = get_settings()
    if settings.mock_aws:
        return _mock_s3_resources(region)

    client = get_client("s3", region)
    resources = []

    buckets = client.list_buckets().get("Buckets", [])
    for bucket in buckets:
        name = bucket["Name"]
        try:
            pab = client.get_public_access_block(Bucket=name)
            public_blocked = all(pab["PublicAccessBlockConfiguration"].values())
        except Exception:
            public_blocked = False

        try:
            versioning = client.get_bucket_versioning(Bucket=name)
            versioning_enabled = versioning.get("Status") == "Enabled"
        except Exception:
            versioning_enabled = False

        try:
            enc = client.get_bucket_encryption(Bucket=name)
            encryption_enabled = bool(enc.get("ServerSideEncryptionConfiguration"))
        except Exception:
            encryption_enabled = False

        try:
            lc = client.get_bucket_lifecycle_configuration(Bucket=name)
            has_lifecycle_policy = bool(lc.get("Rules"))
        except Exception:
            has_lifecycle_policy = False

        try:
            tags_resp = client.get_bucket_tagging(Bucket=name)
            tags = {t["Key"]: t["Value"] for t in tags_resp.get("TagSet", [])}
        except Exception:
            tags = {}

        last_accessed_days = _get_s3_last_accessed_days(name, region)
        size_gb, object_count = _get_s3_size_and_count(name, region)

        resources.append({
            "resource_id": name,
            "resource_type": "S3",
            "region": region,
            "name": name,
            "state": "active",
            "tags": tags,
            "raw_data": {
                "public_access_blocked": public_blocked,
                "versioning_enabled": versioning_enabled,
                "encryption_enabled": encryption_enabled,
                "has_lifecycle_policy": has_lifecycle_policy,
                "last_accessed_days": last_accessed_days,
                "size_gb": size_gb,
                "object_count": object_count,
            },
        })
    return resources
