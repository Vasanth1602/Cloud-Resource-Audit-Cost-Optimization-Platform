from __future__ import annotations

from typing import Any


def evaluate_storage_rules(resource: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Evaluate EBS volumes, S3 buckets, EIPs, and Snapshots against governance rules.
    Returns a list of violation dictionaries.
    """
    violations = []
    raw = resource.get("raw_data", {})
    rtype = resource.get("resource_type", "")
    rid = resource["resource_id"]
    region = resource["region"]

    # ── EBS Rules ───────────────────────────────────────────────────
    if rtype == "EBS":
        # EBS-001: Unattached volume (cost waste)
        if resource.get("state") == "available":
            size_gb = raw.get("size_gb", 0)
            estimated_cost = round(size_gb * 0.10, 2)
            violations.append({
                "rule_id": "EBS-001", "severity": "HIGH",
                "message": f"EBS volume {rid} ({size_gb}GB) is unattached. Estimated waste: ${estimated_cost}/month.",
                "recommendation": "Snapshot and delete unattached volumes. Consider lifecycle policies.",
                "compliance_framework": "FinOps",
                "resource_id": rid, "resource_type": "EBS", "region": region,
            })

        # EBS-002: Unencrypted volume
        if not raw.get("storage_encrypted", raw.get("encrypted", True)):
            violations.append({
                "rule_id": "EBS-002", "severity": "CRITICAL",
                "message": f"EBS volume {rid} is not encrypted at rest.",
                "recommendation": "Create an encrypted snapshot and restore as a new encrypted volume.",
                "compliance_framework": "CIS-AWS",
                "resource_id": rid, "resource_type": "EBS", "region": region,
            })

        # EBS-003: gp2 → gp3 recommendation (~20% cheaper, better baseline perf)
        if raw.get("volume_type") == "gp2":
            violations.append({
                "rule_id": "EBS-003", "severity": "LOW",
                "message": f"EBS volume {rid} uses gp2. gp3 is ~20% cheaper with better baseline performance.",
                "recommendation": "Modify volume type from gp2 to gp3 in the EC2 console (zero downtime).",
                "compliance_framework": "FinOps",
                "resource_id": rid, "resource_type": "EBS", "region": region,
            })

    # ── S3 Rules ─────────────────────────────────────────────────────
    elif rtype == "S3":
        # S3-001: Public access not blocked
        if not raw.get("public_access_blocked", True):
            violations.append({
                "rule_id": "S3-001", "severity": "CRITICAL",
                "message": f"S3 bucket {rid} does not have public access block enabled.",
                "recommendation": "Enable S3 Block Public Access at bucket level. Audit bucket policies.",
                "compliance_framework": "CIS-AWS",
                "resource_id": rid, "resource_type": "S3", "region": region,
            })

        # S3-002: Versioning disabled
        if not raw.get("versioning_enabled", False):
            violations.append({
                "rule_id": "S3-002", "severity": "MEDIUM",
                "message": f"S3 bucket {rid} does not have versioning enabled.",
                "recommendation": "Enable versioning to protect against accidental deletion.",
                "compliance_framework": "Governance",
                "resource_id": rid, "resource_type": "S3", "region": region,
            })

        # S3-003: No server-side encryption
        if not raw.get("encryption_enabled", False):
            violations.append({
                "rule_id": "S3-003", "severity": "HIGH",
                "message": f"S3 bucket {rid} does not have server-side encryption enabled.",
                "recommendation": "Enable SSE-S3 or SSE-KMS encryption on the bucket.",
                "compliance_framework": "CIS-AWS",
                "resource_id": rid, "resource_type": "S3", "region": region,
            })

        # S3-004: No lifecycle policy (objects accumulate, cost grows)
        if not raw.get("has_lifecycle_policy", False):
            violations.append({
                "rule_id": "S3-004", "severity": "MEDIUM",
                "message": f"S3 bucket {rid} has no lifecycle policy configured.",
                "recommendation": "Add a lifecycle policy to expire old objects/versions and reduce storage cost.",
                "compliance_framework": "FinOps",
                "resource_id": rid, "resource_type": "S3", "region": region,
            })

        # S3-005: No access in 90+ days (idle bucket — wasted storage cost)
        last_accessed_days = raw.get("last_accessed_days", 0)
        if last_accessed_days and last_accessed_days > 90:
            violations.append({
                "rule_id": "S3-005", "severity": "MEDIUM",
                "message": (
                    f"S3 bucket {rid} has had no measurable access in {last_accessed_days} days. "
                    "It may be idle."
                ),
                "recommendation": "Review bucket contents and consider archiving to S3 Glacier or deleting if unused.",
                "compliance_framework": "FinOps",
                "resource_id": rid, "resource_type": "S3", "region": region,
            })

    # ── EIP Rules ────────────────────────────────────────────────────
    elif rtype == "EIP":
        # EIP-001: Unassociated Elastic IP ($0.005/hr when idle)
        if not raw.get("associated", False):
            violations.append({
                "rule_id": "EIP-001", "severity": "HIGH",
                "message": f"Elastic IP {rid} is not associated with any instance or NAT gateway.",
                "recommendation": "Release unassociated Elastic IPs to avoid charges (~$3.60/month each).",
                "compliance_framework": "FinOps",
                "resource_id": rid, "resource_type": "EIP", "region": region,
            })

    # ── Snapshot Rules ───────────────────────────────────────────────
    elif rtype == "SNAPSHOT":
        # SNAP-001: Old orphaned snapshot (>30 days, not linked to AMI)
        age_days = raw.get("age_days", 0)
        if age_days > 30 and not raw.get("ami_id"):
            size_gb = raw.get("size_gb", 0)
            estimated_cost = round(size_gb * 0.05, 2)
            violations.append({
                "rule_id": "SNAP-001", "severity": "LOW",
                "message": f"Snapshot {rid} is {age_days} days old and not linked to any AMI. Cost: ~${estimated_cost}/month.",
                "recommendation": "Review and delete snapshots older than 30 days not needed for recovery.",
                "compliance_framework": "FinOps",
                "resource_id": rid, "resource_type": "SNAPSHOT", "region": region,
            })

    return violations
