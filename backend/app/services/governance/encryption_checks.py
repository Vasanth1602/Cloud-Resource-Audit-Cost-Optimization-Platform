from __future__ import annotations

from typing import Any


def check_encryption(resource: dict[str, Any]) -> list[dict[str, Any]]:
    violations = []
    rtype = resource.get("resource_type", "")
    rid = resource["resource_id"]
    region = resource.get("region", "")
    raw = resource.get("raw_data", {})

    if rtype == "RDS":
        if not raw.get("storage_encrypted", True):
            violations.append({
                "rule_id": "ENC-001",
                "severity": "CRITICAL",
                "message": f"RDS instance {rid} storage is not encrypted.",
                "recommendation": "Enable encryption by creating a new encrypted snapshot and restoring.",
                "compliance_framework": "CIS-AWS",
                "resource_id": rid,
                "resource_type": rtype,
                "region": region,
            })
        if raw.get("publicly_accessible", False):
            violations.append({
                "rule_id": "ENC-002",
                "severity": "CRITICAL",
                "message": f"RDS instance {rid} is publicly accessible.",
                "recommendation": "Move RDS to private subnet. Remove public accessibility.",
                "compliance_framework": "CIS-AWS",
                "resource_id": rid,
                "resource_type": rtype,
                "region": region,
            })

    return violations
