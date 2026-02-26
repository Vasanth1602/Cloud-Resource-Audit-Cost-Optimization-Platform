from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import get_settings
from app.utils.aws_client_factory import get_client

# Over-provisioned RDS classes — flag if CPU is low
_LARGE_DB_CLASSES = {
    "db.r5.xlarge", "db.r5.2xlarge", "db.r5.4xlarge", "db.r5.8xlarge",
    "db.r6g.xlarge", "db.r6g.2xlarge", "db.r6g.4xlarge",
    "db.m5.xlarge", "db.m5.2xlarge", "db.m5.4xlarge",
    "db.m6g.xlarge", "db.m6g.2xlarge",
}


def _get_rds_metric(db_id: str, region: str, metric: str, stat: str = "Average", period_days: int = 7) -> float:
    """Fetch a single CloudWatch RDS metric average over the last N days."""
    try:
        cw = get_client("cloudwatch", region)
        end = datetime.now(tz=timezone.utc)
        start = end - timedelta(days=period_days)
        resp = cw.get_metric_statistics(
            Namespace="AWS/RDS",
            MetricName=metric,
            Dimensions=[{"Name": "DBInstanceIdentifier", "Value": db_id}],
            StartTime=start,
            EndTime=end,
            Period=period_days * 86400,
            Statistics=[stat],
        )
        points = resp.get("Datapoints", [])
        if points:
            return round(points[0][stat], 2)
    except Exception:
        pass
    return 0.0


def _mock_rds_resources(region: str) -> list[dict[str, Any]]:
    instance_classes = [
        "db.t3.micro", "db.t3.small", "db.m5.large",
        "db.r5.xlarge", "db.r5.2xlarge",
    ]
    engines = ["mysql", "postgres", "aurora-postgresql"]
    resources = []
    for i in range(random.randint(1, 3)):
        engine = random.choice(engines)
        instance_class = random.choice(instance_classes)
        avg_connections = random.uniform(0.5, 150.0)
        avg_cpu = random.uniform(1.0, 85.0)
        allocated_gb = random.choice([20, 100, 500, 1000])
        # Storage autoscaling: MaxAllocatedStorage > AllocatedStorage means it's enabled
        max_allocated_gb = allocated_gb * 2 if random.choice([True, False]) else allocated_gb
        resources.append({
            "resource_id": f"db-{uuid.uuid4().hex[:12].upper()}",
            "resource_type": "RDS",
            "region": region,
            "name": f"app-db-{i + 1:02d}",
            "state": random.choice(["available", "available", "stopped"]),
            "tags": {
                "Environment": random.choice(["production", "staging", ""]),
                "Owner": random.choice(["team-backend", ""]),
            },
            "raw_data": {
                "engine": engine,
                "engine_version": "15.3" if "postgres" in engine else "8.0.28",
                "instance_class": instance_class,
                "multi_az": random.choice([True, False]),
                "storage_encrypted": random.choice([True, True, False]),
                "publicly_accessible": random.choice([False, False, True]),
                "allocated_storage_gb": allocated_gb,
                "max_allocated_storage_gb": max_allocated_gb,
                "storage_autoscaling_enabled": max_allocated_gb > allocated_gb,
                "avg_cpu_percent": round(avg_cpu, 2),
                "avg_connections": round(avg_connections, 2),
            },
        })
    return resources


def scan_rds(region: str) -> list[dict[str, Any]]:
    settings = get_settings()
    if settings.mock_aws:
        return _mock_rds_resources(region)

    client = get_client("rds", region)
    paginator = client.get_paginator("describe_db_instances")
    resources = []

    for page in paginator.paginate():
        for db in page["DBInstances"]:
            db_id = db["DBInstanceIdentifier"]
            try:
                tags_resp = client.list_tags_for_resource(
                    ResourceName=db.get("DBInstanceArn", "")
                )
                tags = {t["Key"]: t["Value"] for t in tags_resp.get("TagList", [])}
            except Exception:
                tags = {}

            allocated_gb = db.get("AllocatedStorage", 0)
            max_allocated_gb = db.get("MaxAllocatedStorage", allocated_gb)

            # CloudWatch metrics for running instances only
            db_state = db.get("DBInstanceStatus")
            avg_cpu = 0.0
            avg_connections = 0.0
            if db_state == "available":
                avg_cpu = _get_rds_metric(db_id, region, "CPUUtilization")
                avg_connections = _get_rds_metric(db_id, region, "DatabaseConnections")

            resources.append({
                "resource_id": db_id,
                "resource_type": "RDS",
                "region": region,
                "name": db_id,
                "state": db_state,
                "tags": tags,
                "raw_data": {
                    "engine": db.get("Engine"),
                    "engine_version": db.get("EngineVersion"),
                    "instance_class": db.get("DBInstanceClass"),
                    "multi_az": db.get("MultiAZ", False),
                    "storage_encrypted": db.get("StorageEncrypted", False),
                    "publicly_accessible": db.get("PubliclyAccessible", False),
                    "allocated_storage_gb": allocated_gb,
                    "max_allocated_storage_gb": max_allocated_gb,
                    "storage_autoscaling_enabled": max_allocated_gb > allocated_gb,
                    "avg_cpu_percent": avg_cpu,
                    "avg_connections": avg_connections,
                },
            })
    return resources
