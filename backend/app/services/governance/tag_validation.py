from __future__ import annotations

from typing import Any

MANDATORY_TAGS = {"Environment", "Owner", "Project"}


def validate_tags(resource: dict[str, Any]) -> list[dict[str, Any]]:
    violations = []
    tags = resource.get("tags", {})
    rid = resource["resource_id"]
    rtype = resource.get("resource_type", "UNKNOWN")
    region = resource.get("region", "")

    missing = [t for t in MANDATORY_TAGS if not tags.get(t)]
    if missing:
        violations.append({
            "rule_id": "TAG-001",
            "severity": "LOW",
            "message": f"{rtype} {rid} is missing mandatory tags: {', '.join(sorted(missing))}.",
            "recommendation": "Apply tags: Environment, Owner, Project for cost attribution and accountability.",
            "compliance_framework": "Governance",
            "resource_id": rid,
            "resource_type": rtype,
            "region": region,
        })

    # Check for empty tag values
    empty = [k for k, v in tags.items() if k in MANDATORY_TAGS and not v]
    if empty:
        violations.append({
            "rule_id": "TAG-002",
            "severity": "LOW",
            "message": f"{rtype} {rid} has empty mandatory tag values: {', '.join(sorted(empty))}.",
            "recommendation": "Ensure all mandatory tags have meaningful non-empty values.",
            "compliance_framework": "Governance",
            "resource_id": rid,
            "resource_type": rtype,
            "region": region,
        })

    return violations
