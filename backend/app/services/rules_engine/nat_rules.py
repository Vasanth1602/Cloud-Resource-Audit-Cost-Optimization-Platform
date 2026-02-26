from __future__ import annotations

from typing import Any

# NAT Gateway is expensive: ~$32.40/month fixed + $0.045/GB data transfer
_NAT_FIXED_MONTHLY_COST = 32.40


def evaluate_nat_rules(resource: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Evaluate NAT Gateway resources against governance rules.
    Returns a list of violation dictionaries.
    """
    violations = []
    raw = resource.get("raw_data", {})
    rid = resource["resource_id"]
    region = resource["region"]
    name = resource.get("name", rid)

    # NAT-001: Low data transfer (<1 GB over 7 days) — likely unnecessary NAT Gateway
    # NAT costs ~$32.40/month in fixed charges regardless of traffic
    data_gb = raw.get("data_transfer_gb", 0.0)
    if data_gb < 1.0:
        violations.append({
            "rule_id": "NAT-001",
            "severity": "HIGH",
            "message": (
                f"NAT Gateway '{name}' ({rid}) transferred only {data_gb:.3f} GB "
                f"over the last 7 days — extremely low utilization for a resource "
                f"costing ~${_NAT_FIXED_MONTHLY_COST:.2f}/month in fixed charges."
            ),
            "recommendation": (
                "Review whether workloads in this subnet require internet access. "
                "Consider replacing with a VPC Endpoint for AWS services (S3, DynamoDB, ECR) "
                "or eliminating the NAT Gateway if no outbound internet access is required. "
                f"Potential saving: ~${_NAT_FIXED_MONTHLY_COST:.2f}+/month."
            ),
            "compliance_framework": "FinOps",
            "resource_id": rid,
            "resource_type": "NAT",
            "region": region,
        })

    return violations
