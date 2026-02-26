"""
Recommendations Engine
======================
Transforms detected violations into ranked, dollar-estimated savings actions.

Output shape per recommendation:
{
    "id":                    str,         # unique UUID
    "scan_id":               str,
    "category":              str,         # Compute | Storage | Database | Network | Governance
    "rule_id":               str,         # e.g. "EC2-002"
    "resource_id":           str,
    "resource_type":         str,
    "region":                str,
    "title":                 str,         # short action title
    "description":           str,         # 1-2 sentence context
    "action":                str,         # concrete next step
    "estimated_monthly_savings": float,  # USD
    "confidence":            str,         # HIGH | MEDIUM | LOW
    "severity":              str,         # from the originating violation
}
"""
from __future__ import annotations

import uuid
from typing import Any

# ---------------------------------------------------------------------------
# Rule metadata: rule_id → (category, title, description, action, confidence)
# ---------------------------------------------------------------------------
_RULE_META: dict[str, dict[str, str]] = {
    # EC2
    "EC2-001": {
        "category":    "Compute",
        "title":       "Terminate stopped EC2 instance",
        "description": "Stopped EC2 instances still accrue EBS volume charges. "
                       "If this instance has been stopped intentionally, verify it is no longer needed.",
        "action":      "Create an AMI snapshot if needed, then terminate the instance.",
        "confidence":  "HIGH",
    },
    "EC2-002": {
        "category":    "Compute",
        "title":       "Rightsize or stop idle EC2 instance",
        "description": "Instance has averaged < 5% CPU over 7 days — it is effectively idle.",
        "action":      "Stop the instance if unused, or rightsize to a smaller type within the same family.",
        "confidence":  "HIGH",
    },
    "EC2-003": {
        "category":    "Governance",
        "title":       "Apply mandatory tags to EC2 instance",
        "description": "Missing Environment, Owner, or Project tags prevent cost attribution and ownership tracking.",
        "action":      "Apply mandatory tags via AWS Console, CLI, or enforce via SCP/Config rules.",
        "confidence":  "HIGH",
    },
    "EC2-004": {
        "category":    "Governance",
        "title":       "Remove public IP from EC2 instance",
        "description": "EC2 instance has a public IP address assigned without apparent need.",
        "action":      "Review security group rules and use a load balancer or VPN instead of a direct public IP.",
        "confidence":  "MEDIUM",
    },
    "EC2-005": {
        "category":    "Compute",
        "title":       "Rightsize oversized EC2 instance",
        "description": "Instance type is one size larger than needed based on sustained low CPU utilization.",
        "action":      "Change instance type to the next smaller size in the same family (live resize for t3/m5/c5).",
        "confidence":  "HIGH",
    },
    "EC2-006": {
        "category":    "Compute",
        "title":       "Move EC2 instance to Auto Scaling Group",
        "description": "Standalone On-Demand instance has no automatic recovery or scale-in. "
                       "ASGs prevent idle over-spend on low-traffic periods.",
        "action":      "Create a launch template and ASG; migrate instance. Enables Spot/Mixed capacity.",
        "confidence":  "MEDIUM",
    },
    "EC2-007": {
        "category":    "Compute",
        "title":       "Switch to Spot pricing for eligible EC2 instance",
        "description": "Instance family supports Spot pricing at 60–70% savings for stateless workloads.",
        "action":      "Convert to Spot instance or use an ASG with Spot/On-Demand capacity mix.",
        "confidence":  "MEDIUM",
    },
    "EC2-008": {
        "category":    "Compute",
        "title":       "Purchase Reserved Instance for long-running EC2",
        "description": "Instance has been running continuously as On-Demand for > 30 days.",
        "action":      "Purchase a 1-year Convertible RI via AWS Cost Explorer RI recommendations.",
        "confidence":  "MEDIUM",
    },
    # EBS
    "EBS-001": {
        "category":    "Storage",
        "title":       "Delete unattached EBS volume",
        "description": "Volume is not attached to any instance and accumulating charges at $0.10/GB/month.",
        "action":      "Take a final snapshot if needed, then delete the volume.",
        "confidence":  "HIGH",
    },
    "EBS-002": {
        "category":    "Governance",
        "title":       "Enable encryption on EBS volume",
        "description": "Unencrypted EBS volume violates encryption-at-rest policy.",
        "action":      "Create an encrypted snapshot and restore to a new encrypted volume.",
        "confidence":  "HIGH",
    },
    "EBS-003": {
        "category":    "Storage",
        "title":       "Migrate gp2 EBS volume to gp3",
        "description": "gp3 volumes deliver the same baseline IOPS as gp2 at ~20% lower cost.",
        "action":      "Use AWS Console or CLI to modify volume type from gp2 to gp3 (zero downtime).",
        "confidence":  "HIGH",
    },
    # S3
    "S3-001": {
        "category":    "Governance",
        "title":       "Block public access on S3 bucket",
        "description": "Bucket does not have all Block Public Access settings enabled — data may be exposed.",
        "action":      "Enable all four Block Public Access settings on the bucket and at the account level.",
        "confidence":  "HIGH",
    },
    "S3-002": {
        "category":    "Storage",
        "title":       "Enable S3 versioning",
        "description": "Bucket versioning is disabled — accidental deletes or overwrites are not recoverable.",
        "action":      "Enable versioning and configure a lifecycle rule to expire old versions after 30–90 days.",
        "confidence":  "MEDIUM",
    },
    "S3-003": {
        "category":    "Storage",
        "title":       "Add S3 lifecycle policy to control storage growth",
        "description": "Bucket has no lifecycle policy — objects accumulate indefinitely at Standard tier pricing.",
        "action":      "Add a lifecycle rule to transition objects to Intelligent-Tiering or Glacier after 30+ days.",
        "confidence":  "HIGH",
    },
    "S3-004": {
        "category":    "Storage",
        "title":       "Remove or archive idle S3 bucket",
        "description": "Bucket has had no CloudWatch activity for 90+ days.",
        "action":      "Verify the bucket is unused, archive contents to Glacier if needed, then delete.",
        "confidence":  "MEDIUM",
    },
    # EIP
    "EIP-001": {
        "category":    "Network",
        "title":       "Release unassociated Elastic IP",
        "description": "Unassociated EIPs are billed at ~$3.60/month per address.",
        "action":      "Release the Elastic IP address if no longer needed.",
        "confidence":  "HIGH",
    },
    # Snapshots
    "SNAPSHOT-001": {
        "category":    "Storage",
        "title":       "Delete orphaned EBS snapshot",
        "description": "Snapshot is older than 30 days and has no associated AMI.",
        "action":      "Delete the snapshot if no longer required for backup or recovery.",
        "confidence":  "MEDIUM",
    },
    # Load Balancers
    "LB-001": {
        "category":    "Network",
        "title":       "Review low-traffic load balancer",
        "description": "Load balancer has fewer than 10 requests/day — may be unused.",
        "action":      "Verify target group membership and delete the LB if no longer serving traffic.",
        "confidence":  "MEDIUM",
    },
    "LB-002": {
        "category":    "Network",
        "title":       "Delete orphaned load balancer (zero listeners)",
        "description": "Load balancer has no listeners — it is serving no traffic.",
        "action":      "Delete this load balancer immediately to stop fixed hourly charges.",
        "confidence":  "HIGH",
    },
    # NAT Gateway
    "NAT-001": {
        "category":    "Network",
        "title":       "Remove or replace low-utilization NAT Gateway",
        "description": "NAT Gateway transferred < 1 GB over 7 days — extremely low for ~$32.40/month fixed cost.",
        "action":      "Replace with VPC Endpoint (free for S3/DynamoDB) or remove if outbound internet not needed.",
        "confidence":  "HIGH",
    },
    # RDS
    "RDS-001": {
        "category":    "Database",
        "title":       "Stop or remove idle RDS instance",
        "description": "RDS instance had fewer than 5 connections over 7 days — likely unused.",
        "action":      "Stop the instance (saves compute cost) or take a final snapshot and delete.",
        "confidence":  "HIGH",
    },
    "RDS-002": {
        "category":    "Database",
        "title":       "Downsize over-provisioned RDS instance",
        "description": "Large RDS class running with < 20% CPU — significantly over-provisioned.",
        "action":      "Use blue/green deployment to resize to the next smaller instance class, saving ~50%.",
        "confidence":  "HIGH",
    },
    "RDS-003": {
        "category":    "Database",
        "title":       "Enable RDS storage autoscaling",
        "description": "Storage autoscaling is disabled — manual expansion required when disk fills.",
        "action":      "Set MaxAllocatedStorage on the RDS instance to enable transparent autoscaling.",
        "confidence":  "HIGH",
    },
}

# ---------------------------------------------------------------------------
# Savings formulas: rule_id → function(resource_raw_data) → float (USD/month)
# ---------------------------------------------------------------------------
def _savings(rule_id: str, raw: dict[str, Any]) -> float:
    """Estimate monthly savings in USD for a given rule violation."""
    r = rule_id

    if r == "EC2-001":
        # Stopped EC2: mainly the EBS cost. Assume 50 GB average attached volume.
        return round(50 * 0.10, 2)

    if r == "EC2-002":
        # Idle instance — estimate ~70% savings by stopping or downsizing.
        # Without knowing instance price, use $0.10/hr On-Demand average × 730 hr × 70%
        return round(0.10 * 730 * 0.70, 2)

    if r == "EC2-005":
        # Rightsize one size down = ~50% cost reduction on instance compute
        return round(0.10 * 730 * 0.50, 2)

    if r == "EC2-007":
        # Spot saves ~65% over On-Demand for Spot-eligible families
        return round(0.10 * 730 * 0.65, 2)

    if r == "EC2-008":
        # 1-yr Convertible RI saves ~30–40% — use 35% average
        return round(0.10 * 730 * 0.35, 2)

    if r == "EBS-001":
        size_gb = raw.get("size_gb", 20)
        return round(size_gb * 0.10, 2)

    if r == "EBS-003":
        size_gb = raw.get("size_gb", 50)
        return round(size_gb * 0.10 * 0.20, 2)  # gp3 is ~20% cheaper

    if r == "EIP-001":
        return 3.60

    if r == "SNAPSHOT-001":
        size_gb = raw.get("size_gb", 10)
        return round(size_gb * 0.05, 2)

    if r == "LB-002":
        return 22.0  # ALB/NLB fixed charge ~$16–22/month

    if r == "LB-001":
        return 16.0

    if r == "NAT-001":
        return 32.40  # Fixed NAT Gateway charge

    if r == "RDS-001":
        # Idle DB — stopping saves ~100% of compute. Estimate $50–200/mo.
        return 100.0

    if r == "RDS-002":
        # Rightsizing saves ~50% of compute
        return 120.0

    if r in ("EC2-003", "EC2-004", "EC2-006",
             "EBS-002", "S3-001", "S3-002", "S3-003", "S3-004",
             "RDS-003"):
        # Governance / risk rules — no direct monetary savings model
        return 0.0

    return 0.0


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------
def generate_recommendations(
    scan_id: str,
    violations: list[dict[str, Any]],
    resources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Convert violations into ranked recommendations.

    - One recommendation per violation
    - Enriched with resource raw_data for accurate savings formulas
    - Sorted descending by estimated_monthly_savings
    """
    # Build resource lookup for raw_data access
    resource_map: dict[str, dict[str, Any]] = {
        r["resource_id"]: r for r in resources
    }

    recommendations: list[dict[str, Any]] = []

    for v in violations:
        rule_id = v.get("rule_id", "")
        meta = _RULE_META.get(rule_id)
        if not meta:
            continue  # Unknown or unmapped rule — skip

        resource_id = v.get("resource_id", "")
        resource = resource_map.get(resource_id, {})
        raw = resource.get("raw_data", {})

        savings = _savings(rule_id, raw)

        recommendations.append({
            "id":                        str(uuid.uuid4()),
            "scan_id":                   scan_id,
            "category":                  meta["category"],
            "rule_id":                   rule_id,
            "resource_id":               resource_id,
            "resource_type":             v.get("resource_type", ""),
            "region":                    v.get("region", ""),
            "title":                     meta["title"],
            "description":               meta["description"],
            "action":                    meta["action"],
            "estimated_monthly_savings": savings,
            "confidence":                meta["confidence"],
            "severity":                  v.get("severity", "LOW"),
        })

    # Sort: highest savings first, then by severity within zero-savings items
    _sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    recommendations.sort(
        key=lambda r: (
            -r["estimated_monthly_savings"],
            _sev_order.get(r["severity"].upper(), 4),
        )
    )

    return recommendations
