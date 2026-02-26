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

# Instance families that are strongly Spot-eligible (stateless / fault-tolerant)
_SPOT_ELIGIBLE_FAMILIES = {
    "t3", "t3a", "t4g", "m5", "m5a", "m6i", "m6a",
    "c5", "c5a", "c6i", "c6a", "r5", "r5a", "r6i",
}

# Families with strong Reserved Instance savings (predictable, long-running)
_RI_CANDIDATE_FAMILIES = {"m5", "m6i", "c5", "c6i", "r5", "r6i", "t3"}


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

    # Rule EC2-006: Not in an Auto Scaling Group
    # Standalone On-Demand instances have no automatic recovery or scale-in,
    # increasing cost risk during idle periods.
    in_asg = raw.get("in_asg", False)
    if state == "running" and not in_asg:
        violations.append({
            "rule_id": "EC2-006",
            "severity": "LOW",
            "message": (
                f"EC2 instance {resource['resource_id']} ({itype or 'unknown type'}) "
                "is running outside an Auto Scaling Group."
            ),
            "recommendation": (
                "Consider migrating to an ASG for automatic recovery, scale-in during low demand, "
                "and Spot/Mixed capacity support."
            ),
            "compliance_framework": "FinOps",
            "resource_id": resource["resource_id"],
            "resource_type": "EC2",
            "region": resource["region"],
        })

    # Rule EC2-007: Spot-eligible instance running On-Demand with low CPU
    # Spot can save 60–90% for fault-tolerant, stateless workloads.
    spot_eligible = raw.get("spot_eligible", False)
    instance_family = itype.split(".")[0] if itype else ""
    if (
        state == "running"
        and spot_eligible
        and not in_asg  # ASG can manage Spot natively — flag only standalone instances
        and avg_cpu < 40.0
    ):
        violations.append({
            "rule_id": "EC2-007",
            "severity": "MEDIUM",
            "message": (
                f"EC2 instance {resource['resource_id']} is a {itype} ({avg_cpu:.1f}% avg CPU) "
                "eligible for Spot pricing but running as On-Demand."
            ),
            "recommendation": (
                f"Migrate to a Spot instance or use an ASG with Spot/On-Demand mix. "
                f"Spot pricing for {instance_family} typically saves 60–70% vs On-Demand."
            ),
            "compliance_framework": "FinOps",
            "resource_id": resource["resource_id"],
            "resource_type": "EC2",
            "region": resource["region"],
        })

    # Rule EC2-008: Reserved Instance candidate
    # Running > 30 days continuously on an RI-eligible family → strong RI signal.
    ri_candidate = raw.get("ri_candidate", False)
    launch_days = raw.get("launch_days_ago", 0)
    if state == "running" and ri_candidate and instance_family in _RI_CANDIDATE_FAMILIES:
        violations.append({
            "rule_id": "EC2-008",
            "severity": "LOW",
            "message": (
                f"EC2 instance {resource['resource_id']} ({itype}) has been running for "
                f"{launch_days} days as On-Demand. It is a strong Reserved Instance candidate."
            ),
            "recommendation": (
                f"Purchase a 1-year Convertible RI for {itype} to save ~30–40% vs On-Demand. "
                "Use AWS Cost Explorer RI recommendations for exact pricing."
            ),
            "compliance_framework": "FinOps",
            "resource_id": resource["resource_id"],
            "resource_type": "EC2",
            "region": resource["region"],
        })

    return violations
