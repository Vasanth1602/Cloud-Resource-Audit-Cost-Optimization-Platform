from __future__ import annotations

from typing import Any

# Rightsizing map: oversized type → suggested smaller type
_RIGHTSIZE_MAP = {
    "m5.xlarge":   "m5.large",
    "m5.2xlarge":  "m5.xlarge",
    "m5.4xlarge":  "m5.2xlarge",
    "m6i.xlarge":  "m6i.large",
    "m6i.2xlarge": "m6i.xlarge",
    "c5.xlarge":   "c5.large",
    "c5.2xlarge":  "c5.xlarge",
    "c5.4xlarge":  "c5.2xlarge",
    "c6i.xlarge":  "c6i.large",
    "c6i.2xlarge": "c6i.xlarge",
    "r5.xlarge":   "r5.large",
    "r5.2xlarge":  "r5.xlarge",
    "r5.4xlarge":  "r5.2xlarge",
    "t3.medium":   "t3.small",
    "t3.large":    "t3.medium",
    "t3.xlarge":   "t3.large",
}


def evaluate_ec2_rules(resource: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Evaluate EC2 resources against governance rules.
    Returns a list of violation dictionaries.
    """
    violations = []
    raw = resource.get("raw_data", {})
    tags = resource.get("tags", {})
    state = resource.get("state", "")

    # Rule EC2-001: Stopped EC2 instance (waste — still incurs EBS cost)
    if state == "stopped":
        violations.append({
            "rule_id": "EC2-001",
            "severity": "MEDIUM",
            "message": f"EC2 instance {resource['resource_id']} is stopped but still incurring EBS storage costs.",
            "recommendation": "Terminate idle stopped instances or create an AMI and terminate.",
            "compliance_framework": "FinOps",
            "resource_id": resource["resource_id"],
            "resource_type": "EC2",
            "region": resource["region"],
        })

    # Rule EC2-002: Low CPU utilization (idle instance — cost waste)
    avg_cpu = raw.get("avg_cpu_percent", 100.0)
    if state == "running" and avg_cpu < 5.0:
        violations.append({
            "rule_id": "EC2-002",
            "severity": "HIGH",
            "message": f"EC2 instance {resource['resource_id']} has avg CPU of {avg_cpu:.1f}% — likely idle.",
            "recommendation": "Rightsize to a smaller instance type or terminate if unused.",
            "compliance_framework": "FinOps",
            "resource_id": resource["resource_id"],
            "resource_type": "EC2",
            "region": resource["region"],
        })

    # Rule EC2-003: Missing mandatory tags
    mandatory_tags = {"Environment", "Owner", "Project"}
    missing = [t for t in mandatory_tags if not tags.get(t)]
    if missing:
        violations.append({
            "rule_id": "EC2-003",
            "severity": "LOW",
            "message": f"EC2 instance {resource['resource_id']} missing tags: {', '.join(missing)}.",
            "recommendation": "Apply mandatory tags for cost attribution and ownership tracking.",
            "compliance_framework": "Governance",
            "resource_id": resource["resource_id"],
            "resource_type": "EC2",
            "region": resource["region"],
        })

    # Rule EC2-004: Public IP assigned (potential security exposure)
    if raw.get("public_ip") and state == "running":
        violations.append({
            "rule_id": "EC2-004",
            "severity": "MEDIUM",
            "message": f"EC2 instance {resource['resource_id']} has a public IP ({raw['public_ip']}).",
            "recommendation": "Move behind a load balancer. Remove direct public IP if not required.",
            "compliance_framework": "CIS-AWS",
            "resource_id": resource["resource_id"],
            "resource_type": "EC2",
            "region": resource["region"],
        })

    # Rule EC2-005: Oversized instance — large type with consistently low CPU
    itype = raw.get("instance_type", "")
    suggested = _RIGHTSIZE_MAP.get(itype)
    if state == "running" and suggested and avg_cpu < 20.0:
        violations.append({
            "rule_id": "EC2-005",
            "severity": "MEDIUM",
            "message": (
                f"EC2 instance {resource['resource_id']} is a {itype} with only "
                f"{avg_cpu:.1f}% avg CPU — likely oversized."
            ),
            "recommendation": f"Consider rightsizing from {itype} to {suggested} (estimated ~50% cost saving).",
            "compliance_framework": "FinOps",
            "resource_id": resource["resource_id"],
            "resource_type": "EC2",
            "region": resource["region"],
        })

    return violations
