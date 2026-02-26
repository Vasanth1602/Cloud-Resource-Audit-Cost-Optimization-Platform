from app.core.config import get_settings
from app.utils.aws_client_factory import get_client

import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any



def _mock_ec2_resources(region: str) -> list[dict[str, Any]]:
    instance_types = ["t3.micro", "t3.small", "t3.medium", "m5.large", "m5.xlarge", "c5.2xlarge"]
    states = ["running", "running", "running", "stopped", "stopped"]
    resources = []
    for i in range(random.randint(4, 8)):
        itype = random.choice(instance_types)
        state = random.choice(states)
        cpu = random.uniform(1.0, 8.0) if state == "running" else 0.0
        resources.append({
            "resource_id": f"i-{uuid.uuid4().hex[:16]}",
            "resource_type": "EC2",
            "region": region,
            "name": f"app-server-{i+1:02d}",
            "state": state,
            "tags": {
                "Environment": random.choice(["production", "staging", "dev", ""]),
                "Owner": random.choice(["team-platform", "team-backend", ""]),
                "Project": random.choice(["cloud-audit", "ecommerce", ""]),
            },
            "raw_data": {
                "instance_type": itype,
                "avg_cpu_percent": round(cpu, 2),
                "launch_time": "2025-11-01T00:00:00Z",
                "vpc_id": f"vpc-{uuid.uuid4().hex[:8]}",
                "public_ip": f"54.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}" if state == "running" else None,
            },
        })
    return resources


def _get_avg_cpu(instance_id: str, region: str, period_days: int = 7) -> float:
    """Fetch average CPU utilization from CloudWatch for the last N days."""
    try:
        cw = get_client("cloudwatch", region)
        end = datetime.now(tz=timezone.utc)
        start = end - timedelta(days=period_days)
        resp = cw.get_metric_statistics(
            Namespace="AWS/EC2",
            MetricName="CPUUtilization",
            Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
            StartTime=start,
            EndTime=end,
            Period=period_days * 86400,  # one single data point for the whole window
            Statistics=["Average"],
        )
        points = resp.get("Datapoints", [])
        if points:
            return round(points[0]["Average"], 2)
    except Exception:
        pass
    return 0.0


def scan_ec2(region: str) -> list[dict[str, Any]]:
    settings = get_settings()
    if settings.mock_aws:
        return _mock_ec2_resources(region)

    client = get_client("ec2", region)
    paginator = client.get_paginator("describe_instances")
    resources = []

    for page in paginator.paginate():
        for reservation in page["Reservations"]:
            for instance in reservation["Instances"]:
                instance_id = instance["InstanceId"]
                name = next(
                    (t["Value"] for t in instance.get("Tags", []) if t["Key"] == "Name"),
                    None,
                )
                tags = {t["Key"]: t["Value"] for t in instance.get("Tags", [])}
                state = instance["State"]["Name"]

                # Fetch real CPU for running instances only
                avg_cpu = _get_avg_cpu(instance_id, region) if state == "running" else 0.0

                resources.append({
                    "resource_id": instance_id,
                    "resource_type": "EC2",
                    "region": region,
                    "name": name,
                    "state": state,
                    "tags": tags,
                    "raw_data": {
                        "instance_type": instance.get("InstanceType"),
                        "launch_time": str(instance.get("LaunchTime")),
                        "vpc_id": instance.get("VpcId"),
                        "public_ip": instance.get("PublicIpAddress"),
                        "avg_cpu_percent": avg_cpu,
                    },
                })
    return resources
