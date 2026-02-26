from __future__ import annotations

import random
from typing import Any


def check_security_groups(resource: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Check EC2 instances for security group misconfigurations.
    In mock mode, randomly generates SG violations for realism.
    """
    violations = []
    rid = resource["resource_id"]
    region = resource.get("region", "")
    raw = resource.get("raw_data", {})

    # Mock: randomly assign open SG violations
    if resource.get("resource_type") == "EC2" and resource.get("state") == "running":
        if random.random() < 0.3:  # 30% chance of open SSH
            violations.append({
                "rule_id": "SG-001",
                "severity": "CRITICAL",
                "message": f"EC2 {rid} has security group allowing SSH (port 22) from 0.0.0.0/0.",
                "recommendation": "Restrict SSH access to known IPs or use AWS Systems Manager Session Manager.",
                "compliance_framework": "CIS-AWS",
                "resource_id": rid,
                "resource_type": "EC2",
                "region": region,
            })

        if random.random() < 0.2:  # 20% chance of open RDP
            violations.append({
                "rule_id": "SG-002",
                "severity": "CRITICAL",
                "message": f"EC2 {rid} has security group allowing RDP (port 3389) from 0.0.0.0/0.",
                "recommendation": "Restrict RDP to a VPN or bastion host range. Consider SSM instead.",
                "compliance_framework": "CIS-AWS",
                "resource_id": rid,
                "resource_type": "EC2",
                "region": region,
            })

    return violations
