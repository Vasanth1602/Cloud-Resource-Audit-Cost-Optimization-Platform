from __future__ import annotations

from typing import Any

# NAT Gateway fixed costs: ~$0.045/hr = ~$32.40/month (plus data transfer)
_NAT_FIXED_MONTHLY_COST = 32.40


def evaluate_lb_rules(resource: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Evaluate Load Balancer (ALB/NLB) resources against governance rules.
    Returns a list of violation dictionaries.
    """
    violations = []
    raw = resource.get("raw_data", {})
    rid = resource["resource_id"]
    region = resource["region"]
    name = resource.get("name", rid)
    lb_type = raw.get("lb_type", "LB")

    # LB-001: Low request count — likely unused (< 10 req/day over 7 days)
    avg_req = raw.get("avg_request_count_per_day", 0.0)
    listener_count = raw.get("listener_count", 0)
    if listener_count > 0 and avg_req < 10.0:
        violations.append({
            "rule_id": "LB-001",
            "severity": "HIGH",
            "message": (
                f"{lb_type} '{name}' ({rid}) has an average of {avg_req:.1f} requests/day "
                f"over the last 7 days — likely unused or abandoned."
            ),
            "recommendation": (
                "Review target groups and associated services. "
                "Delete unused load balancers to save ~$16–$22/month in ALB/NLB fixed charges."
            ),
            "compliance_framework": "FinOps",
            "resource_id": rid,
            "resource_type": "LB",
            "region": region,
        })

    # LB-002: Zero listeners — fully orphaned load balancer
    if listener_count == 0:
        violations.append({
            "rule_id": "LB-002",
            "severity": "CRITICAL",
            "message": (
                f"{lb_type} '{name}' ({rid}) has zero listeners configured. "
                "It is serving no traffic and accumulating fixed hourly charges."
            ),
            "recommendation": (
                "Delete this load balancer immediately. "
                "A load balancer with no listeners is an orphaned resource with no operational value."
            ),
            "compliance_framework": "FinOps",
            "resource_id": rid,
            "resource_type": "LB",
            "region": region,
        })

    return violations
