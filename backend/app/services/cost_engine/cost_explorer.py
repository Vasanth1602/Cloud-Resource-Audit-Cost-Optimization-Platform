from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any

from app.core.config import get_settings
from app.utils.aws_client_factory import get_client

# ---------------------------------------------------------------------------
# Real AWS helpers
# ---------------------------------------------------------------------------

def get_real_cost_data(regions: list[str]) -> list[dict[str, Any]]:
    """
    Fetch MTD cost data from AWS Cost Explorer API (MONTHLY granularity).
    Cost Explorer is a global service — always called with us-east-1.
    Requires: ce:GetCostAndUsage permission.
    """
    client = get_client("ce", "us-east-1")
    today = datetime.utcnow()
    period_start = today.replace(day=1).strftime("%Y-%m-%d")
    period_end = today.strftime("%Y-%m-%d")

    if period_start == period_end:
        period_start = (today - timedelta(days=1)).replace(day=1).strftime("%Y-%m-%d")

    try:
        resp = client.get_cost_and_usage(
            TimePeriod={"Start": period_start, "End": period_end},
            Granularity="MONTHLY",
            GroupBy=[
                {"Type": "DIMENSION", "Key": "SERVICE"},
                {"Type": "DIMENSION", "Key": "REGION"},
            ],
            Metrics=["UnblendedCost"],
        )
    except Exception as e:
        raise RuntimeError(f"Cost Explorer API failed: {e}")

    records = []
    for result in resp.get("ResultsByTime", []):
        for group in result.get("Groups", []):
            keys = group.get("Keys", [])
            if len(keys) < 2:
                continue
            service, region = keys[0], keys[1]
            amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
            currency = group["Metrics"]["UnblendedCost"]["Unit"]

            if not regions or region in regions or region == "":
                records.append({
                    "service": service,
                    "region": region or "global",
                    "amount": round(amount, 4),
                    "currency": currency,
                    "period_start": period_start,
                    "period_end": period_end,
                    "granularity": "MONTHLY",
                })
    return records


def get_real_daily_trend(days: int = 14) -> list[dict[str, Any]]:
    """Fetch daily total cost for the last N days from Cost Explorer."""
    client = get_client("ce", "us-east-1")
    today = datetime.utcnow()
    period_start = (today - timedelta(days=days)).strftime("%Y-%m-%d")
    period_end = today.strftime("%Y-%m-%d")

    try:
        resp = client.get_cost_and_usage(
            TimePeriod={"Start": period_start, "End": period_end},
            Granularity="DAILY",
            Metrics=["UnblendedCost"],
        )
    except Exception as e:
        raise RuntimeError(f"Daily trend API failed: {e}")

    trend = []
    for result in resp.get("ResultsByTime", []):
        amount = sum(
            float(m["Amount"])
            for m in result.get("Total", {}).values()
        )
        trend.append({
            "date": result["TimePeriod"]["Start"],
            "amount": round(amount, 2),
        })
    return sorted(trend, key=lambda x: x["date"])


def get_real_cost_by_tag(tag_key: str = "Environment") -> list[dict[str, Any]]:
    """Group current month costs by a tag key using Cost Explorer."""
    client = get_client("ce", "us-east-1")
    today = datetime.utcnow()
    period_start = today.replace(day=1).strftime("%Y-%m-%d")
    period_end = today.strftime("%Y-%m-%d")

    if period_start == period_end:
        period_start = (today - timedelta(days=1)).replace(day=1).strftime("%Y-%m-%d")

    try:
        resp = client.get_cost_and_usage(
            TimePeriod={"Start": period_start, "End": period_end},
            Granularity="MONTHLY",
            GroupBy=[{"Type": "TAG", "Key": tag_key}],
            Metrics=["UnblendedCost"],
        )
    except Exception:
        return []

    results = []
    for result in resp.get("ResultsByTime", []):
        for group in result.get("Groups", []):
            tag_val = (group.get("Keys") or ["untagged"])[0]
            tag_val = tag_val.replace(f"{tag_key}$", "") or "untagged"
            amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
            results.append({"tag": tag_val, "amount": round(amount, 2)})
    return sorted(results, key=lambda x: x["amount"], reverse=True)


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

def get_mock_cost_data(regions: list[str]) -> list[dict[str, Any]]:
    """Generate realistic mock cost data per service/region (MONTHLY)."""
    services = {
        "Amazon EC2":        (500,  3000),
        "Amazon RDS":        (200,  1500),
        "Amazon S3":         (50,   500),
        "Amazon EBS":        (100,  800),
        "AWS Lambda":        (10,   200),
        "Amazon CloudFront": (50,   300),
        "Amazon Route 53":   (5,    50),
        "AWS Data Transfer": (100,  600),
    }
    today = datetime.utcnow()
    period_start = today.replace(day=1).strftime("%Y-%m-%d")
    period_end = today.strftime("%Y-%m-%d")

    records = []
    for region in regions:
        for service, (low, high) in services.items():
            records.append({
                "service": service,
                "region": region,
                "amount": round(random.uniform(low, high), 2),
                "currency": "USD",
                "period_start": period_start,
                "period_end": period_end,
                "granularity": "MONTHLY",
            })
    return records


def get_mock_daily_trend(days: int = 14) -> list[dict[str, Any]]:
    """Generate mock daily cost trend with realistic day-over-day variance."""
    today = datetime.utcnow()
    base = random.uniform(800, 1800)  # baseline daily spend
    trend = []
    for i in range(days):
        date = (today - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        # Add slight upward drift + random noise (weekends cheaper)
        day_of_week = (today - timedelta(days=days - 1 - i)).weekday()
        multiplier = 0.7 if day_of_week >= 5 else 1.0
        amount = round(base * multiplier * random.uniform(0.85, 1.20), 2)
        trend.append({"date": date, "amount": amount})
    return trend


def get_mock_cost_by_tag() -> list[dict[str, Any]]:
    """Generate mock cost breakdown by Environment tag."""
    return [
        {"tag": "production",  "amount": round(random.uniform(2000, 5000), 2)},
        {"tag": "staging",     "amount": round(random.uniform(500,  1500), 2)},
        {"tag": "development", "amount": round(random.uniform(200,  800),  2)},
        {"tag": "untagged",    "amount": round(random.uniform(100,  600),  2)},
    ]


# ---------------------------------------------------------------------------
# Unified entry points
# ---------------------------------------------------------------------------

def get_cost_data(regions: list[str]) -> list[dict[str, Any]]:
    """Unified entry point: real or mock based on settings."""
    settings = get_settings()
    return get_mock_cost_data(regions) if settings.mock_aws else get_real_cost_data(regions)


def get_daily_trend(days: int = 14) -> list[dict[str, Any]]:
    """Unified: 14-day daily cost trend."""
    settings = get_settings()
    return get_mock_daily_trend(days) if settings.mock_aws else get_real_daily_trend(days)


def get_cost_by_tag(tag_key: str = "Environment") -> list[dict[str, Any]]:
    """Unified: MTD cost grouped by a tag key."""
    settings = get_settings()
    return get_mock_cost_by_tag() if settings.mock_aws else get_real_cost_by_tag(tag_key)


# ---------------------------------------------------------------------------
# Summary builder
# ---------------------------------------------------------------------------

_WASTE_RULE_SERVICES: dict[str, str] = {
    "EBS-001": "Amazon EBS",
    "EIP-001": "Amazon EC2",
    "SNAPSHOT-001": "Amazon EBS",
    "EC2-001": "Amazon EC2",
    "EC2-002": "Amazon EC2",
    "EC2-005": "Amazon EC2",
    "LB-001": "Amazon EC2",
    "LB-002": "Amazon EC2",
    "NAT-001": "Amazon VPC",
    "RDS-001": "Amazon RDS",
    "RDS-002": "Amazon RDS",
}


def _compute_waste_by_service(
    violations: list[dict[str, Any]],
    service_totals: dict[str, float],
) -> list[dict[str, Any]]:
    """
    Estimate waste-per-AWS-service by mapping violation rule IDs → service names.
    Uses a conservative 10-30% waste factor per rule hit, capped by actual MTD spend.
    """
    waste_map: dict[str, float] = {}
    for v in violations:
        rule_id = v.get("rule_id", "")
        svc = _WASTE_RULE_SERVICES.get(rule_id)
        if svc and svc in service_totals:
            # Each violation contributes a conservative 2% estimated waste
            waste_map[svc] = waste_map.get(svc, 0.0) + service_totals[svc] * 0.02

    # Cap at 35% of the service's actual MTD spend
    results = []
    for svc, waste in waste_map.items():
        cap = service_totals.get(svc, 0) * 0.35
        results.append({
            "service": svc,
            "estimated_waste": round(min(waste, cap), 2),
        })
    return sorted(results, key=lambda x: x["estimated_waste"], reverse=True)


def build_cost_summary(
    cost_records: list[dict[str, Any]],
    violations: list[dict[str, Any]] | None = None,
    include_trend: bool = True,
    include_tags: bool = True,
) -> dict[str, Any]:
    """
    Aggregate cost records into a structured summary.
    Optionally includes daily trend, tag breakdown, and waste-by-service.
    """
    violations = violations or []
    total = sum(r["amount"] for r in cost_records)

    # Top services
    service_totals: dict[str, float] = {}
    for r in cost_records:
        service_totals[r["service"]] = service_totals.get(r["service"], 0) + r["amount"]
    top_services = sorted(
        [{"service": k, "amount": round(v, 2)} for k, v in service_totals.items()],
        key=lambda x: x["amount"], reverse=True,
    )[:6]

    # Top regions
    region_totals: dict[str, float] = {}
    for r in cost_records:
        region_totals[r["region"]] = region_totals.get(r["region"], 0) + r["amount"]
    top_regions = sorted(
        [{"region": k, "amount": round(v, 2)} for k, v in region_totals.items()],
        key=lambda x: x["amount"], reverse=True,
    )

    # Waste estimation — driven by violations when available, else random fallback
    if violations:
        waste_by_service = _compute_waste_by_service(violations, service_totals)
        estimated_waste = sum(w["estimated_waste"] for w in waste_by_service)
        estimated_waste = round(estimated_waste, 2)
    else:
        estimated_waste = round(total * random.uniform(0.15, 0.30), 2)
        waste_by_service = []

    waste_pct = round((estimated_waste / total) * 100, 1) if total > 0 else 0.0
    period = cost_records[0]["period_start"][:7] if cost_records else "N/A"

    summary: dict[str, Any] = {
        "total_monthly_cost": round(total, 2),
        "currency": "USD",
        "period": period,
        "top_services": top_services,
        "top_regions": top_regions,
        "estimated_monthly_waste": estimated_waste,
        "waste_percentage": waste_pct,
        "waste_by_service": waste_by_service,
    }

    # Daily trend — always fetch (light call, 14 days)
    if include_trend:
        try:
            summary["daily_trend"] = get_daily_trend(days=14)
        except Exception:
            summary["daily_trend"] = []

    # Cost by tag — tag grouping by Environment
    if include_tags:
        try:
            summary["cost_by_tag"] = get_cost_by_tag("Environment")
        except Exception:
            summary["cost_by_tag"] = []

    return summary
