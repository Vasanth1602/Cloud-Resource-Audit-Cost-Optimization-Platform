from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.core import store
from app.services.cost_engine.cost_explorer import get_cost_data
from app.services.governance.encryption_checks import check_encryption
from app.services.governance.security_group_checks import check_security_groups
from app.services.governance.tag_validation import validate_tags
from app.services.rules_engine.ec2_rules import evaluate_ec2_rules
from app.services.rules_engine.scoring import compute_risk_score
from app.services.rules_engine.storage_rules import evaluate_storage_rules
from app.services.scanner.ebs_scanner import scan_ebs
from app.services.scanner.ec2_scanner import scan_ec2
from app.services.scanner.eip_scanner import scan_eip
from app.services.scanner.lb_scanner import scan_lb
from app.services.scanner.nat_scanner import scan_nat
from app.services.scanner.rds_scanner import scan_rds
from app.services.scanner.s3_scanner import scan_s3
from app.services.scanner.snapshot_scanner import scan_snapshots
from app.services.rules_engine.lb_rules import evaluate_lb_rules
from app.services.rules_engine.nat_rules import evaluate_nat_rules
from app.services.rules_engine.rds_rules import evaluate_rds_rules
from app.services.recommendations import generate_recommendations

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scans", tags=["audit"])

SCANNERS = {
    "EC2":      scan_ec2,
    "EBS":      scan_ebs,
    "S3":       scan_s3,
    "RDS":      scan_rds,
    "EIP":      scan_eip,
    "SNAPSHOT": scan_snapshots,
    "LB":       scan_lb,
    "NAT":      scan_nat,
}


class ScanRequest(BaseModel):
    regions: list[str] = ["us-east-1"]
    resource_types: Optional[list[str]] = None


def _run_scan(scan_id: str, regions: list[str], resource_types: list[str]) -> None:
    """Background task: scan AWS and populate in-memory store."""
    try:
        store.scan_sessions[scan_id]["status"] = "running"
        all_resources: list[dict[str, Any]] = []
        all_violations: list[dict[str, Any]] = []

        for region in regions:
            for rtype, scanner_fn in SCANNERS.items():
                if resource_types and rtype not in resource_types:
                    continue
                try:
                    logger.info(f"Scanning {rtype} in {region}")
                    resources = scanner_fn(region)

                    for r in resources:
                        r["scan_id"] = scan_id
                        r["id"] = str(uuid.uuid4())

                        # Rules engine — dispatch by resource type
                        if rtype == "EC2":
                            violations = evaluate_ec2_rules(r)
                        elif rtype == "RDS":
                            violations = evaluate_rds_rules(r)
                        elif rtype == "LB":
                            violations = evaluate_lb_rules(r)
                        elif rtype == "NAT":
                            violations = evaluate_nat_rules(r)
                        else:
                            violations = evaluate_storage_rules(r)

                        # Governance checks
                        violations += validate_tags(r)
                        if rtype == "EC2":
                            violations += check_security_groups(r)
                        if rtype == "RDS":
                            violations += check_encryption(r)

                        risk_score = compute_risk_score(violations)
                        r["risk_score"] = risk_score
                        r["violation_count"] = len(violations)
                        all_resources.append(r)

                        for v in violations:
                            all_violations.append({
                                "id": str(uuid.uuid4()),
                                "scan_id": scan_id,
                                "resource_id": r["resource_id"],
                                "resource_type": rtype,
                                "region": region,
                                "rule_id": v.get("rule_id", "UNKNOWN"),
                                "severity": v.get("severity", "medium"),
                                "message": v.get("message", ""),
                                "remediation": v.get("recommendation", ""),
                            })

                except Exception as e:
                    logger.error(f"Scanner {rtype} failed in {region}: {e}")

        # Cost data
        try:
            cost_data = get_cost_data(regions)
            store.scan_costs[scan_id] = cost_data
        except Exception as e:
            logger.warning(f"Cost data failed: {e}")
            store.scan_costs[scan_id] = []

        # Recommendations — generated from all violations
        try:
            recs = generate_recommendations(scan_id, all_violations, all_resources)
            store.scan_recommendations[scan_id] = recs
        except Exception as e:
            logger.warning(f"Recommendations generation failed: {e}")
            store.scan_recommendations[scan_id] = []

        store.scan_resources[scan_id] = all_resources
        store.scan_violations[scan_id] = all_violations

        store.scan_sessions[scan_id].update({
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
            "resource_count": len(all_resources),
            "violation_count": len(all_violations),
        })
        store.save()
        logger.info(f"Scan {scan_id} done: {len(all_resources)} resources, {len(all_violations)} violations")

    except Exception as e:
        store.scan_sessions[scan_id]["status"] = "failed"
        store.scan_sessions[scan_id]["error"] = str(e)
        logger.error(f"Scan {scan_id} failed: {e}")


@router.post("", status_code=202)
async def trigger_scan(payload: ScanRequest, background_tasks: BackgroundTasks):
    scan_id = str(uuid.uuid4())
    rtypes = payload.resource_types or list(SCANNERS.keys())
    store.scan_sessions[scan_id] = {
        "id": scan_id,
        "status": "pending",
        "regions": payload.regions,
        "resource_types": rtypes,
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "resource_count": 0,
        "violation_count": 0,
    }
    background_tasks.add_task(_run_scan, scan_id, payload.regions, rtypes)
    return {"scan_id": scan_id, "status": "pending", "message": "Scan started"}


@router.get("")
async def list_scans():
    sessions = sorted(store.scan_sessions.values(), key=lambda s: s["started_at"], reverse=True)
    return {"scans": sessions, "total": len(sessions)}


@router.get("/{scan_id}")
async def get_scan(scan_id: str):
    session = store.scan_sessions.get(scan_id)
    if not session:
        raise HTTPException(status_code=404, detail="Scan not found")
    return session


@router.get("/{scan_id}/resources")
async def get_scan_resources(scan_id: str, page: int = 1, page_size: int = 500,
                              resource_type: Optional[str] = None, region: Optional[str] = None):
    if scan_id not in store.scan_sessions:
        raise HTTPException(status_code=404, detail="Scan not found")

    resources = store.scan_resources.get(scan_id, [])
    if resource_type:
        resources = [r for r in resources if r.get("resource_type") == resource_type]
    if region:
        resources = [r for r in resources if r.get("region") == region]

    total = len(resources)
    start = (page - 1) * page_size
    page_items = resources[start: start + page_size]

    return {
        "scan_id": scan_id,
        "resources": page_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/{scan_id}/violations")
async def get_scan_violations(
    scan_id: str,
    severity: Optional[str] = None,
    resource_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 500,
):
    if scan_id not in store.scan_sessions:
        raise HTTPException(status_code=404, detail="Scan not found")

    violations = store.scan_violations.get(scan_id, [])
    if severity:
        violations = [v for v in violations if (v.get("severity") or "").upper() == severity.upper()]
    if resource_type:
        violations = [v for v in violations if v.get("resource_type") == resource_type]

    # Sort: CRITICAL → HIGH → MEDIUM → LOW
    _order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    violations = sorted(violations, key=lambda v: _order.get((v.get("severity") or "LOW").upper(), 4))

    total = len(violations)
    start = (page - 1) * page_size
    page_items = violations[start: start + page_size]

    # Severity summary counts
    sev_counts: dict[str, int] = {}
    for v in store.scan_violations.get(scan_id, []):
        s = (v.get("severity") or "UNKNOWN").upper()
        sev_counts[s] = sev_counts.get(s, 0) + 1

    return {
        "scan_id": scan_id,
        "violations": page_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
        "severity_summary": sev_counts,
    }


@router.get("/{scan_id}/costs")
async def get_scan_costs(scan_id: str):
    if scan_id not in store.scan_sessions:
        raise HTTPException(status_code=404, detail="Scan not found")

    from app.services.cost_engine.cost_explorer import build_cost_summary
    cost_records = store.scan_costs.get(scan_id, [])
    violations = store.scan_violations.get(scan_id, [])
    summary = build_cost_summary(cost_records, violations=violations) if cost_records else {}
    return {
        "scan_id": scan_id,
        "records": cost_records,
        "summary": summary,
    }


@router.get("/{scan_id}/recommendations")
async def get_scan_recommendations(scan_id: str, category: Optional[str] = None):
    if scan_id not in store.scan_sessions:
        raise HTTPException(status_code=404, detail="Scan not found")

    recs = store.scan_recommendations.get(scan_id, [])
    if category:
        recs = [r for r in recs if r.get("category", "").lower() == category.lower()]

    total_savings = round(sum(r.get("estimated_monthly_savings", 0) for r in recs), 2)

    return {
        "scan_id": scan_id,
        "total": len(recs),
        "total_estimated_monthly_savings": total_savings,
        "recommendations": recs,
    }


# ── Export Endpoints ──────────────────────────────────────────────────────────
from fastapi.responses import StreamingResponse


@router.get("/{scan_id}/export/violations.csv")
async def export_violations_csv(scan_id: str):
    """Download violations as a CSV file."""
    if scan_id not in store.scan_sessions:
        raise HTTPException(status_code=404, detail="Scan not found")

    from app.services.export_engine import violations_to_csv
    violations = store.scan_violations.get(scan_id, [])
    csv_content = violations_to_csv(violations)

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=violations-{scan_id[:8]}.csv",
            "Content-Length": str(len(csv_content.encode("utf-8"))),
        },
    )


@router.get("/{scan_id}/export/recommendations.csv")
async def export_recommendations_csv(scan_id: str):
    """Download recommendations as a CSV file."""
    if scan_id not in store.scan_sessions:
        raise HTTPException(status_code=404, detail="Scan not found")

    from app.services.export_engine import recommendations_to_csv
    recs = store.scan_recommendations.get(scan_id, [])
    csv_content = recommendations_to_csv(recs)

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=recommendations-{scan_id[:8]}.csv",
            "Content-Length": str(len(csv_content.encode("utf-8"))),
        },
    )


@router.get("/{scan_id}/export/report.json")
async def export_full_json(scan_id: str):
    """Download complete scan bundle as JSON."""
    if scan_id not in store.scan_sessions:
        raise HTTPException(status_code=404, detail="Scan not found")

    from app.services.export_engine import build_json_bundle
    from app.services.cost_engine.cost_explorer import build_cost_summary

    session = store.scan_sessions[scan_id]
    resources = store.scan_resources.get(scan_id, [])
    violations = store.scan_violations.get(scan_id, [])
    cost_records = store.scan_costs.get(scan_id, [])
    recs = store.scan_recommendations.get(scan_id, [])
    cost_summary = build_cost_summary(cost_records, violations) if cost_records else {}

    json_content = build_json_bundle(session, resources, violations, cost_summary, recs)

    return StreamingResponse(
        iter([json_content]),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=scan-{scan_id[:8]}.json",
            "Content-Length": str(len(json_content.encode("utf-8"))),
        },
    )


@router.get("/{scan_id}/export/report.html")
async def export_html_report(scan_id: str):
    """
    Return a self-contained, print-ready HTML report.
    Open in browser then Ctrl+P / Save as PDF.
    """
    if scan_id not in store.scan_sessions:
        raise HTTPException(status_code=404, detail="Scan not found")

    from app.services.export_engine import build_html_report
    from app.services.cost_engine.cost_explorer import build_cost_summary

    session = store.scan_sessions[scan_id]
    violations = store.scan_violations.get(scan_id, [])
    cost_records = store.scan_costs.get(scan_id, [])
    recs = store.scan_recommendations.get(scan_id, [])
    cost_summary = build_cost_summary(cost_records, violations) if cost_records else {}

    html_content = build_html_report(session, violations, cost_summary, recs)

    return StreamingResponse(
        iter([html_content]),
        media_type="text/html",
        headers={
            "Content-Disposition": f"inline; filename=report-{scan_id[:8]}.html",
        },
    )
