#!/usr/bin/env python3
"""
CLI Report Generator
Usage:
    python scripts/report.py                         # latest scan → stdout JSON
    python scripts/report.py --scan-id <id>          # specific scan
    python scripts/report.py --output report.json    # save to file
    python scripts/report.py --slack                 # post to Slack (reads SLACK_WEBHOOK_URL)
    python scripts/report.py --slack https://hooks.slack.com/...  # explicit URL

Generates a JSON audit report from the in-memory scan store.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Add backend root to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core import store  # noqa: E402 — must be after sys.path patch


def build_report(scan_id: str | None = None) -> dict:
    """Build a structured JSON audit report."""
    # Determine which scan to use
    if scan_id:
        if scan_id not in store.scan_sessions:
            print(f"Error: Scan {scan_id} not found.", file=sys.stderr)
            sys.exit(1)
        session = store.scan_sessions[scan_id]
    else:
        sessions = sorted(
            store.scan_sessions.values(),
            key=lambda s: s["started_at"],
            reverse=True,
        )
        completed = [s for s in sessions if s["status"] == "completed"]
        if not completed:
            print("No completed scans found. Run a scan first.", file=sys.stderr)
            sys.exit(1)
        session = completed[0]
        scan_id = session["id"]

    resources = store.scan_resources.get(scan_id, [])
    violations = store.scan_violations.get(scan_id, [])

    # Severity summary
    sev_counts: dict[str, int] = {}
    for v in violations:
        sev = v.get("severity", "UNKNOWN").upper()
        sev_counts[sev] = sev_counts.get(sev, 0) + 1

    # Group violations by resource type
    by_type: dict[str, list] = {}
    for v in violations:
        rtype = v.get("resource_type", "UNKNOWN")
        by_type.setdefault(rtype, []).append({
            "rule_id": v.get("rule_id"),
            "severity": v.get("severity"),
            "resource_id": v.get("resource_id"),
            "region": v.get("region"),
            "message": v.get("message"),
            "recommendation": v.get("remediation"),
        })

    # Resource counts
    resource_counts: dict[str, int] = {}
    for r in resources:
        rtype = r.get("resource_type", "UNKNOWN")
        resource_counts[rtype] = resource_counts.get(rtype, 0) + 1

    report = {
        "report_meta": {
            "scan_id": scan_id,
            "started_at": session.get("started_at"),
            "completed_at": session.get("completed_at"),
            "regions": session.get("regions", []),
            "status": session.get("status"),
        },
        "summary": {
            "total_resources": len(resources),
            "total_violations": len(violations),
            "resources_by_type": resource_counts,
            "violations_by_severity": sev_counts,
        },
        "violations_by_resource_type": by_type,
        "all_violations": [
            {
                "rule_id": v.get("rule_id"),
                "severity": v.get("severity"),
                "resource_type": v.get("resource_type"),
                "resource_id": v.get("resource_id"),
                "region": v.get("region"),
                "message": v.get("message"),
                "recommendation": v.get("remediation"),
            }
            for v in sorted(
                violations,
                key=lambda x: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(
                    (x.get("severity") or "LOW").upper(), 4
                ),
            )
        ],
    }
    return report


# ─── Slack ────────────────────────────────────────────────────────────────────

_SEV_EMOJI = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🔵"}


def _build_slack_payload(report: dict) -> dict:
    """Convert an audit report dict into a Slack Block Kit message payload."""
    meta = report["report_meta"]
    summary = report["summary"]
    sev = summary.get("violations_by_severity", {})

    region_str = ", ".join(meta.get("regions", []))
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "☁️ AWS Cloud Audit Report", "emoji": True},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Scan ID:*\n`{meta['scan_id'][:8]}…`"},
                {"type": "mrkdwn", "text": f"*Regions:*\n{region_str or 'N/A'}"},
                {"type": "mrkdwn", "text": f"*Total Resources:*\n{summary['total_resources']}"},
                {"type": "mrkdwn", "text": f"*Total Violations:*\n{summary['total_violations']}"},
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Violations by Severity*"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"{_SEV_EMOJI.get(s, '⚪')} *{s}:* {sev.get(s, 0)}"}
                for s in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
            ],
        },
    ]

    # Top 5 worst violations
    top_violations = report["all_violations"][:5]
    if top_violations:
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Top Violations (sorted by severity)*"},
        })
        for v in top_violations:
            emoji = _SEV_EMOJI.get((v.get("severity") or "").upper(), "⚪")
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"{emoji} `{v.get('rule_id', 'N/A')}` — *{v.get('resource_type')}* "
                        f"`{v.get('resource_id', '')}` [{v.get('region', '')}]\n"
                        f"> {v.get('message', '')}"
                    ),
                },
            })

    # Resources by type summary
    res_by_type = summary.get("resources_by_type", {})
    if res_by_type:
        blocks.append({"type": "divider"})
        breakdown = "  ".join(f"*{k}:* {v}" for k, v in sorted(res_by_type.items()))
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Resources Scanned:* {breakdown}"},
        })

    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"Completed at {meta.get('completed_at', 'N/A')} | Cloud Resource Audit Platform",
            }
        ],
    })
    return {"blocks": blocks}


def post_to_slack(report: dict, webhook_url: str) -> None:
    """POST the audit summary to a Slack incoming webhook."""
    import urllib.error
    import urllib.request

    payload = _build_slack_payload(report)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.getcode() == 200:
                print("✅ Slack notification sent successfully.")
            else:
                print(f"⚠️  Slack returned HTTP {resp.getcode()}.", file=sys.stderr)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        print(f"❌ Slack webhook error {exc.code}: {body}", file=sys.stderr)
    except Exception as exc:
        print(f"❌ Failed to send Slack notification: {exc}", file=sys.stderr)


# ─── CLI entry-point ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate AWS audit report from latest scan.")
    parser.add_argument("--scan-id", help="Specific scan ID to report on (default: latest completed)")
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    parser.add_argument(
        "--slack",
        metavar="WEBHOOK_URL",
        nargs="?",
        const=os.environ.get("SLACK_WEBHOOK_URL", ""),
        default=None,
        help=(
            "Post summary to Slack. Optionally pass the webhook URL directly; "
            "otherwise reads SLACK_WEBHOOK_URL from environment."
        ),
    )
    args = parser.parse_args()

    report = build_report(args.scan_id)
    output = json.dumps(report, indent=2, default=str)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Report written to {args.output}")
        print(f"  Total resources : {report['summary']['total_resources']}")
        print(f"  Total violations: {report['summary']['total_violations']}")
        for sev, count in sorted(report["summary"]["violations_by_severity"].items()):
            print(f"    {sev}: {count}")
    else:
        print(output)

    # Slack notification (optional)
    if args.slack is not None:
        webhook_url = args.slack or os.environ.get("SLACK_WEBHOOK_URL", "")
        if not webhook_url:
            print(
                "❌ No Slack webhook URL provided. Pass --slack <URL> or set SLACK_WEBHOOK_URL.",
                file=sys.stderr,
            )
        else:
            post_to_slack(report, webhook_url)


if __name__ == "__main__":
    main()
