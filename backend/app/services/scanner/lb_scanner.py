from __future__ import annotations

import logging
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import get_settings
from app.utils.aws_client_factory import get_client

logger = logging.getLogger(__name__)


def _get_lb_request_count(lb_arn: str, region: str, period_days: int = 7) -> float:
    """Fetch average daily RequestCount from CloudWatch for an ALB/NLB."""
    try:
        cw = get_client("cloudwatch", region)
        end = datetime.now(tz=timezone.utc)
        start = end - timedelta(days=period_days)
        resp = cw.get_metric_statistics(
            Namespace="AWS/ApplicationELB",
            MetricName="RequestCount",
            Dimensions=[{"Name": "LoadBalancer", "Value": lb_arn.split("loadbalancer/")[-1]}],
            StartTime=start,
            EndTime=end,
            Period=period_days * 86400,
            Statistics=["Sum"],
        )
        points = resp.get("Datapoints", [])
        if points:
            total = sum(p["Sum"] for p in points)
            return round(total / period_days, 2)
    except Exception as exc:
        logger.debug("CloudWatch RequestCount for %s failed: %s", lb_arn, exc)
    return 0.0


def _get_nlb_active_connections(lb_arn: str, region: str, period_days: int = 7) -> float:
    """Fetch average ActiveFlowCount for NLB — used as proxy for request activity."""
    try:
        cw = get_client("cloudwatch", region)
        end = datetime.now(tz=timezone.utc)
        start = end - timedelta(days=period_days)
        resp = cw.get_metric_statistics(
            Namespace="AWS/NetworkELB",
            MetricName="ActiveFlowCount",
            Dimensions=[{"Name": "LoadBalancer", "Value": lb_arn.split("loadbalancer/")[-1]}],
            StartTime=start,
            EndTime=end,
            Period=period_days * 86400,
            Statistics=["Average"],
        )
        points = resp.get("Datapoints", [])
        if points:
            return round(points[0]["Average"], 2)
    except Exception as exc:
        logger.debug("CloudWatch ActiveFlowCount for %s failed: %s", lb_arn, exc)
    return 0.0


def _mock_lb_resources(region: str) -> list[dict[str, Any]]:
    names = ["api-gateway-alb", "internal-service-nlb", "prod-web-alb", "dev-alb"]
    lb_types = ["ALB", "NLB"]
    resources = []
    for name in random.sample(names, random.randint(1, 3)):
        lb_type = random.choice(lb_types)
        listener_count = random.randint(0, 2)
        avg_req = random.uniform(0, 500) if listener_count > 0 else 0.0
        resources.append({
            "resource_id": f"arn:aws:elasticloadbalancing:{region}:123456789012:loadbalancer/app/{name}/{uuid.uuid4().hex[:16]}",
            "resource_type": "LB",
            "region": region,
            "name": name,
            "state": random.choice(["active", "active", "provisioning"]),
            "tags": {
                "Environment": random.choice(["production", "staging", ""]),
                "Owner": random.choice(["team-platform", ""]),
            },
            "raw_data": {
                "lb_type": lb_type,
                "dns_name": f"{name}-{random.randint(100000, 999999)}.{region}.elb.amazonaws.com",
                "listener_count": listener_count,
                "avg_request_count_per_day": round(avg_req, 2),
                "scheme": random.choice(["internet-facing", "internal"]),
            },
        })
    return resources


def scan_lb(region: str) -> list[dict[str, Any]]:
    """Scan ALBs and NLBs in the given region."""
    settings = get_settings()
    if settings.mock_aws:
        return _mock_lb_resources(region)

    client = get_client("elbv2", region)
    resources = []
    paginator = client.get_paginator("describe_load_balancers")

    for page in paginator.paginate():
        for lb in page.get("LoadBalancers", []):
            lb_arn = lb["LoadBalancerArn"]
            lb_type_raw = lb.get("Type", "application").lower()
            lb_type = "ALB" if lb_type_raw == "application" else "NLB"

            try:
                tags_resp = client.describe_tags(ResourceArns=[lb_arn])
                tags = {
                    t["Key"]: t["Value"]
                    for tag_desc in tags_resp.get("TagDescriptions", [])
                    for t in tag_desc.get("Tags", [])
                }
            except Exception:
                tags = {}

            try:
                listeners_resp = client.describe_listeners(LoadBalancerArn=lb_arn)
                listener_count = len(listeners_resp.get("Listeners", []))
            except Exception:
                listener_count = 0

            if lb_type == "ALB":
                avg_req = _get_lb_request_count(lb_arn, region)
            else:
                avg_req = _get_nlb_active_connections(lb_arn, region)

            resources.append({
                "resource_id": lb_arn,
                "resource_type": "LB",
                "region": region,
                "name": lb.get("LoadBalancerName"),
                "state": lb.get("State", {}).get("Code", "unknown"),
                "tags": tags,
                "raw_data": {
                    "lb_type": lb_type,
                    "dns_name": lb.get("DNSName"),
                    "listener_count": listener_count,
                    "avg_request_count_per_day": avg_req,
                    "scheme": lb.get("Scheme"),
                },
            })

    return resources
