from __future__ import annotations

from typing import Any

# Large RDS classes — flag for over-provisioning when CPU is low
_LARGE_DB_CLASSES = {
    "db.r5.xlarge", "db.r5.2xlarge", "db.r5.4xlarge", "db.r5.8xlarge",
    "db.r6g.xlarge", "db.r6g.2xlarge", "db.r6g.4xlarge",
    "db.m5.xlarge", "db.m5.2xlarge", "db.m5.4xlarge",
    "db.m6g.xlarge", "db.m6g.2xlarge",
}


def evaluate_rds_rules(resource: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Evaluate RDS instances against cost optimization and governance rules.
    Returns a list of violation dictionaries.
    """
    violations = []
    raw = resource.get("raw_data", {})
    rid = resource["resource_id"]
    region = resource["region"]
    state = resource.get("state", "")
    instance_class = raw.get("instance_class", "")

    # Only evaluate running databases for operational metrics
    if state != "available":
        return violations

    # Rule RDS-001: Idle database — very low connection count
    # Average < 5 connections/day over 7 days signals no active workload
    avg_connections = raw.get("avg_connections", 0.0)
    if avg_connections < 5.0:
        violations.append({
            "rule_id": "RDS-001",
            "severity": "HIGH",
            "message": (
                f"RDS instance {rid} ({instance_class}) had an average of "
                f"{avg_connections:.1f} connections over the last 7 days — "
                "likely idle or unused."
            ),
            "recommendation": (
                "Verify whether this database is actively serving any application. "
                "If unused, stop the instance (saves ~100% of compute cost) or "
                "take a final snapshot and delete it."
            ),
            "compliance_framework": "FinOps",
            "resource_id": rid,
            "resource_type": "RDS",
            "region": region,
        })

    # Rule RDS-002: Over-provisioned large DB instance with low CPU
    # Large/XL classes with < 20% avg CPU are strong candidates for downsizing
    avg_cpu = raw.get("avg_cpu_percent", 0.0)
    if instance_class in _LARGE_DB_CLASSES and avg_cpu < 20.0:
        violations.append({
            "rule_id": "RDS-002",
            "severity": "MEDIUM",
            "message": (
                f"RDS instance {rid} is a {instance_class} with only {avg_cpu:.1f}% "
                "avg CPU utilization — likely over-provisioned for its current workload."
            ),
            "recommendation": (
                "Consider downsizing to the next smaller instance class "
                "(e.g., db.r5.xlarge → db.r5.large) to reduce compute cost by ~50%. "
                "Use a Multi-AZ blue/green deployment for zero-downtime resize."
            ),
            "compliance_framework": "FinOps",
            "resource_id": rid,
            "resource_type": "RDS",
            "region": region,
        })

    # Rule RDS-003: Storage autoscaling not enabled
    # Without autoscaling, storage must be manually expanded — risks outage on full disk
    storage_autoscaling = raw.get("storage_autoscaling_enabled", False)
    if not storage_autoscaling:
        violations.append({
            "rule_id": "RDS-003",
            "severity": "LOW",
            "message": (
                f"RDS instance {rid} does not have storage autoscaling enabled. "
                "Manual storage expansion is required when the disk fills up."
            ),
            "recommendation": (
                "Enable RDS storage autoscaling by setting MaxAllocatedStorage. "
                "This prevents storage-full outages without pre-allocating excess capacity."
            ),
            "compliance_framework": "Governance",
            "resource_id": rid,
            "resource_type": "RDS",
            "region": region,
        })

    return violations
