from app.core.config import get_settings
from app.utils.aws_client_factory import get_client

import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

# Instance families eligible for Spot (stateless, fault-tolerant workloads)
_SPOT_ELIGIBLE_FAMILIES = {
    "t3", "t3a", "t4g", "m5", "m5a", "m6i", "m6a",
    "c5", "c5a", "c6i", "c6a", "r5", "r5a", "r6i",
}

# Instance families with strong RI savings potential (consistent On-Demand usage)
_RI_CANDIDATE_FAMILIES = {"m5", "m6i", "c5", "c6i", "r5", "r6i", "t3"}


def _get_instance_family(instance_type: str) -> str:
    """Extract family prefix from instance type, e.g. 'm5.xlarge' → 'm5'."""
    return instance_type.split(".")[0] if instance_type else ""


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
            Period=period_days * 86400,
            Statistics=["Average"],
        )
        points = resp.get("Datapoints", [])
        if points:
            return round(points[0]["Average"], 2)
    except Exception:
        pass
    return 0.0


def _get_network_gb(instance_id: str, region: str, metric: str, period_days: int = 7) -> float:
    """Fetch NetworkIn or NetworkOut bytes and convert to GB."""
    try:
        cw = get_client("cloudwatch", region)
        end = datetime.now(tz=timezone.utc)
        start = end - timedelta(days=period_days)
        resp = cw.get_metric_statistics(
            Namespace="AWS/EC2",
            MetricName=metric,
            Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
            StartTime=start,
            EndTime=end,
            Period=period_days * 86400,
            Statistics=["Sum"],
        )
        points = resp.get("Datapoints", [])
        if points:
            return round(points[0]["Sum"] / (1024 ** 3), 4)
    except Exception:
        pass
    return 0.0


def _mock_ec2_resources(region: str) -> list[dict[str, Any]]:
    instance_types = [
        "t3.micro", "t3.small", "t3.medium", "t3.large",
        "m5.large", "m5.xlarge", "c5.2xlarge", "r5.xlarge",
    ]
    states = ["running", "running", "running", "stopped", "stopped"]
    asg_names = ["web-asg", "api-asg", ""]
    resources = []
    for i in range(random.randint(4, 8)):
        itype = random.choice(instance_types)
        state = random.choice(states)
        cpu = random.uniform(1.0, 8.0) if state == "running" else 0.0
        family = _get_instance_family(itype)
        asg_name = random.choice(asg_names)

        # Simulate a launch time between 5 and 120 days ago
        launch_days_ago = random.randint(5, 120)
        launch_time = (datetime.now(tz=timezone.utc) - timedelta(days=launch_days_ago)).isoformat()

        resources.append({
            "resource_id": f"i-{uuid.uuid4().hex[:16]}",
            "resource_type": "EC2",
            "region": region,
            "name": f"app-server-{i + 1:02d}",
            "state": state,
            "tags": {
                "Environment": random.choice(["production", "staging", "dev", ""]),
                "Owner": random.choice(["team-platform", "team-backend", ""]),
                "Project": random.choice(["cloud-audit", "ecommerce", ""]),
                **({"aws:autoscaling:groupName": asg_name} if asg_name else {}),
            },
            "raw_data": {
                "instance_type": itype,
                "avg_cpu_percent": round(cpu, 2),
                "launch_time": launch_time,
                "launch_days_ago": launch_days_ago,
                "vpc_id": f"vpc-{uuid.uuid4().hex[:8]}",
                "public_ip": (
                    f"54.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"
                    if state == "running" else None
                ),
                "in_asg": bool(asg_name),
                "spot_eligible": family in _SPOT_ELIGIBLE_FAMILIES,
                "ri_candidate": family in _RI_CANDIDATE_FAMILIES and launch_days_ago > 30,
                "network_in_gb": round(random.uniform(0.1, 50.0), 3) if state == "running" else 0.0,
                "network_out_gb": round(random.uniform(0.1, 20.0), 3) if state == "running" else 0.0,
            },
        })
    return resources


def scan_ec2(region: str) -> list[dict[str, Any]]:
    settings = get_settings()
    if settings.mock_aws:
        return _mock_ec2_resources(region)

    client = get_client("ec2", region)
    paginator = client.get_paginator("describe_instances")
    resources = []
    now = datetime.now(tz=timezone.utc)

    for page in paginator.paginate():
        for reservation in page["Reservations"]:
            for instance in reservation["Instances"]:
                instance_id = instance["InstanceId"]
                tags = {t["Key"]: t["Value"] for t in instance.get("Tags", [])}
                name = tags.get("Name")
                state = instance["State"]["Name"]
                itype = instance.get("InstanceType", "")
                family = _get_instance_family(itype)

                # Fetch real CPU for running instances only
                avg_cpu = _get_avg_cpu(instance_id, region) if state == "running" else 0.0

                # Network metrics for running instances
                network_in_gb = 0.0
                network_out_gb = 0.0
                if state == "running":
                    network_in_gb = _get_network_gb(instance_id, region, "NetworkIn")
                    network_out_gb = _get_network_gb(instance_id, region, "NetworkOut")

                # ASG membership: check for the standard autoscaling tag
                in_asg = bool(tags.get("aws:autoscaling:groupName"))

                # Days since launch
                launch_time = instance.get("LaunchTime")
                launch_days_ago = (now - launch_time).days if launch_time else 0

                # RI candidate: running > 30 days on a RI-eligible family (On-Demand assumed)
                ri_candidate = (
                    family in _RI_CANDIDATE_FAMILIES
                    and launch_days_ago > 30
                    and state == "running"
                )

                resources.append({
                    "resource_id": instance_id,
                    "resource_type": "EC2",
                    "region": region,
                    "name": name,
                    "state": state,
                    "tags": tags,
                    "raw_data": {
                        "instance_type": itype,
                        "launch_time": str(launch_time),
                        "launch_days_ago": launch_days_ago,
                        "vpc_id": instance.get("VpcId"),
                        "public_ip": instance.get("PublicIpAddress"),
                        "avg_cpu_percent": avg_cpu,
                        "in_asg": in_asg,
                        "spot_eligible": family in _SPOT_ELIGIBLE_FAMILIES,
                        "ri_candidate": ri_candidate,
                        "network_in_gb": network_in_gb,
                        "network_out_gb": network_out_gb,
                    },
                })
    return resources
