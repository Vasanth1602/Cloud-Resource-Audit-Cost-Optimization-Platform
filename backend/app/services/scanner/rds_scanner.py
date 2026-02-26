from __future__ import annotations

import random
import uuid
from typing import Any

from app.core.config import get_settings
from app.utils.aws_client_factory import get_client


def _mock_rds_resources(region: str) -> list[dict[str, Any]]:
    instance_classes = ["db.t3.micro", "db.t3.small", "db.m5.large", "db.r5.xlarge"]
    engines = ["mysql", "postgres", "aurora-postgresql"]
    resources = []
    for i in range(random.randint(1, 3)):
        engine = random.choice(engines)
        resources.append({
            "resource_id": f"db-{uuid.uuid4().hex[:12].upper()}",
            "resource_type": "RDS",
            "region": region,
            "name": f"app-db-{i+1:02d}",
            "state": random.choice(["available", "available", "stopped"]),
            "tags": {
                "Environment": random.choice(["production", "staging", ""]),
                "Owner": random.choice(["team-backend", ""]),
            },
            "raw_data": {
                "engine": engine,
                "engine_version": "15.3" if "postgres" in engine else "8.0.28",
                "instance_class": random.choice(instance_classes),
                "multi_az": random.choice([True, False]),
                "storage_encrypted": random.choice([True, True, False]),
                "publicly_accessible": random.choice([False, False, True]),
                "allocated_storage_gb": random.choice([20, 100, 500]),
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
            tags_resp = client.list_tags_for_resource(
                ResourceName=db.get("DBInstanceArn", "")
            )
            tags = {t["Key"]: t["Value"] for t in tags_resp.get("TagList", [])}
            resources.append({
                "resource_id": db["DBInstanceIdentifier"],
                "resource_type": "RDS",
                "region": region,
                "name": db["DBInstanceIdentifier"],
                "state": db.get("DBInstanceStatus"),
                "tags": tags,
                "raw_data": {
                    "engine": db.get("Engine"),
                    "engine_version": db.get("EngineVersion"),
                    "instance_class": db.get("DBInstanceClass"),
                    "multi_az": db.get("MultiAZ", False),
                    "storage_encrypted": db.get("StorageEncrypted", False),
                    "publicly_accessible": db.get("PubliclyAccessible", False),
                    "allocated_storage_gb": db.get("AllocatedStorage"),
                },
            })
    return resources
