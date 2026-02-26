"""
Export Engine — Phase 5
=======================
Generates downloadable reports from scan data:
  - CSV (violations, recommendations)
  - JSON (full scan bundle)
  - HTML/print-ready report (open in browser, Ctrl+P → Save as PDF)
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Any


# ── CSV Generators ────────────────────────────────────────────────────────────

def violations_to_csv(violations: list[dict[str, Any]]) -> str:
    """Return UTF-8 CSV string for violations."""
    buf = io.StringIO()
    fieldnames = [
        "rule_id", "severity", "resource_type", "resource_id",
        "region", "message", "remediation",
    ]
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\r\n")
    writer.writeheader()
    for v in violations:
        writer.writerow({k: v.get(k, "") for k in fieldnames})
    return buf.getvalue()


def recommendations_to_csv(recommendations: list[dict[str, Any]]) -> str:
    """Return UTF-8 CSV string for recommendations."""
    buf = io.StringIO()
    fieldnames = [
        "category", "rule_id", "resource_type", "resource_id", "region",
        "title", "description", "action",
        "estimated_monthly_savings", "confidence", "severity",
    ]
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\r\n")
    writer.writeheader()
    for r in recommendations:
        writer.writerow({k: r.get(k, "") for k in fieldnames})
    return buf.getvalue()


# ── JSON Bundle ───────────────────────────────────────────────────────────────

def build_json_bundle(
    scan_session: dict[str, Any],
    resources: list[dict[str, Any]],
    violations: list[dict[str, Any]],
    cost_summary: dict[str, Any],
    recommendations: list[dict[str, Any]],
) -> str:
    """Return a formatted JSON string of the complete scan bundle."""
    total_savings = round(
        sum(r.get("estimated_monthly_savings", 0) for r in recommendations), 2
    )
    bundle = {
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "scan": scan_session,
        "summary": {
            "total_resources": len(resources),
            "total_violations": len(violations),
            "total_recommendations": len(recommendations),
            "total_estimated_monthly_savings": total_savings,
        },
        "cost_summary": cost_summary,
        "violations": violations,
        "recommendations": recommendations,
    }
    return json.dumps(bundle, indent=2, default=str)


# ── HTML Report Helpers (Python 3.9 compatible) ───────────────────────────────

_SEV_COLORS: dict[str, str] = {
    "CRITICAL": "#ef4444",
    "HIGH":     "#f97316",
    "MEDIUM":   "#f59e0b",
    "LOW":      "#6b7280",
}

_CAT_COLORS: dict[str, str] = {
    "Compute":    "#3b82f6",
    "Storage":    "#8b5cf6",
    "Database":   "#10b981",
    "Network":    "#0ea5e9",
    "Governance": "#6b7280",
}


def _sev_badge(sev: str) -> str:
    """Render an HTML severity badge — Python 3.9 compatible."""
    color = _SEV_COLORS.get(sev.upper(), "#6b7280")
    style = (
        "background:" + color + "22;"
        "color:" + color + ";"
        "border:1px solid " + color + "44;"
        "border-radius:4px;padding:1px 8px;font-size:11px;font-weight:700"
    )
    return '<span style="' + style + '">' + sev + "</span>"


def _td(val: str, align: str = "left") -> str:
    """Render a table cell — Python 3.9 compatible."""
    style = "padding:8px 10px;text-align:" + align + ";border-bottom:1px solid #e2e8f0"
    return '<td style="' + style + '">' + val + "</td>"


def _build_vio_rows(violations: list[dict[str, Any]]) -> str:
    rows = []
    for v in violations[:200]:
        rid = v.get("resource_id", "")
        rid_cell = '<code style="font-size:11px">' + rid + "</code>"
        row = (
            "<tr>"
            + _td(v.get("rule_id", ""))
            + _td(_sev_badge(v.get("severity", "LOW")))
            + _td(v.get("resource_type", ""))
            + _td(rid_cell)
            + _td(v.get("region", ""))
            + _td(v.get("message", ""))
            + "</tr>"
        )
        rows.append(row)
    return "".join(rows)


def _build_rec_rows(recommendations: list[dict[str, Any]]) -> str:
    rows = []
    for r in recommendations[:100]:
        cat = r.get("category", "")
        color = _CAT_COLORS.get(cat, "#6b7280")
        savings = r.get("estimated_monthly_savings", 0)
        if savings > 0:
            savings_str = '<strong style="color:#10b981">$' + "{:,.2f}".format(savings) + "</strong>"
        else:
            savings_str = "—"
        cat_span = '<span style="color:' + color + ';font-weight:700">' + cat + "</span>"
        row = (
            "<tr>"
            + _td(cat_span)
            + _td(r.get("title", ""))
            + _td(_sev_badge(r.get("severity", "LOW")))
            + _td(savings_str, "right")
            + _td(r.get("action", ""))
            + "</tr>"
        )
        rows.append(row)
    return "".join(rows)


def _build_sev_pills(sev_counts: dict[str, int]) -> str:
    pills = []
    for s in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        color = _SEV_COLORS.get(s, "#6b7280")
        count = sev_counts.get(s, 0)
        pill = (
            '<div style="background:' + color + '18;border:1px solid ' + color + '44;'
            'border-radius:6px;padding:10px 20px;text-align:center">'
            '<div style="font-size:20px;font-weight:800;color:' + color + '">' + str(count) + "</div>"
            '<div style="font-size:10px;font-weight:700;color:' + color + '">' + s + "</div>"
            "</div>"
        )
        pills.append(pill)
    return "".join(pills)


def _build_svc_bars(top_services: list[dict[str, Any]]) -> str:
    if not top_services:
        return ""
    max_svc = max((s["amount"] for s in top_services), default=1)
    bars = []
    for s in top_services:
        pct = int((s["amount"] / max_svc) * 120)
        bars.append(
            '<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">'
            '<div style="width:160px;font-size:12px;color:#475569">' + s["service"] + "</div>"
            '<div style="flex:1;background:#e2e8f0;border-radius:4px;height:8px">'
            '<div style="width:' + str(pct) + 'px;max-width:100%;'
            'background:linear-gradient(90deg,#3b82f6,#8b5cf6);'
            'height:8px;border-radius:4px"></div></div>'
            '<div style="font-size:12px;font-weight:700;color:#1e293b;'
            'min-width:80px;text-align:right">$' + "{:,.2f}".format(s["amount"]) + "</div>"
            "</div>"
        )
    return "".join(bars)


# ── HTML Report ───────────────────────────────────────────────────────────────

def build_html_report(
    scan_session: dict[str, Any],
    violations: list[dict[str, Any]],
    cost_summary: dict[str, Any],
    recommendations: list[dict[str, Any]],
) -> str:
    """
    Generate a self-contained, print-optimised HTML report.
    Browser can print as PDF via Ctrl+P → Save as PDF.
    No external dependencies — pure HTML/CSS.
    """
    scan_id = scan_session.get("id", "")
    regions = ", ".join(scan_session.get("regions") or [])
    completed_raw = scan_session.get("completed_at") or scan_session.get("started_at") or ""
    completed = completed_raw[:19].replace("T", " ") + " UTC" if completed_raw else ""
    resource_count = scan_session.get("resource_count", 0)
    violation_count = scan_session.get("violation_count", 0)

    total_savings = round(sum(r.get("estimated_monthly_savings", 0) for r in recommendations), 2)
    total_cost = cost_summary.get("total_monthly_cost", 0)
    waste_pct = cost_summary.get("waste_percentage", 0)
    period = cost_summary.get("period", "N/A")
    top_services = cost_summary.get("top_services", [])[:5]

    # Severity counts
    sev_counts: dict[str, int] = {}
    for v in violations:
        s = (v.get("severity") or "UNKNOWN").upper()
        sev_counts[s] = sev_counts.get(s, 0) + 1

    # Pre-render HTML fragments
    vio_rows = _build_vio_rows(violations)
    rec_rows = _build_rec_rows(recommendations)
    sev_pills = _build_sev_pills(sev_counts)
    svc_bars = _build_svc_bars(top_services)
    generated = datetime.utcnow().strftime("%Y-%m-%d %H:%M") + " UTC"

    # Conditional cost section
    cost_section = ""
    if top_services:
        cost_section = (
            "<h2>Cost Intelligence</h2>"
            "<h3>Top Services by MTD Spend</h3>"
            '<div style="margin-bottom:24px">' + svc_bars + "</div>"
        )

    vio_violation_header = "Full Violations Log ({} of {})".format(
        min(len(violations), 200), len(violations)
    )
    rec_header = "Savings Recommendations ({} actions \u00b7 ${}/month)".format(
        len(recommendations), "{:,.2f}".format(total_savings)
    )

    vio_pill_color = "#ef4444" if violation_count > 0 else "#10b981"
    scan_id_short = scan_id[:8] if scan_id else ""

    waste_label = "MTD Spend ({}) \u00b7 {}% waste".format(period, waste_pct)

    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>CloudAudit Report &mdash; {scan_id_short}</title>
  <style>
    *{{ box-sizing:border-box; margin:0; padding:0 }}
    body{{ font-family:'Segoe UI',system-ui,sans-serif; color:#1e293b; background:#fff; font-size:13px; line-height:1.5 }}
    .page{{ max-width:1100px; margin:0 auto; padding:40px 48px }}
    h1{{ font-size:22px; font-weight:800; color:#0f172a; margin-bottom:4px }}
    h2{{ font-size:15px; font-weight:700; color:#0f172a; margin:28px 0 12px }}
    h3{{ font-size:13px; font-weight:600; color:#475569; text-transform:uppercase; letter-spacing:.5px; margin:20px 0 8px }}
    .meta{{ font-size:12px; color:#64748b; margin-bottom:28px }}
    .kpi-grid{{ display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:28px }}
    .kpi{{ background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:16px 18px }}
    .kpi-val{{ font-size:24px; font-weight:800; color:#0f172a; margin-bottom:2px }}
    .kpi-label{{ font-size:11px; color:#64748b; text-transform:uppercase; letter-spacing:.5px }}
    table{{ width:100%; border-collapse:collapse; margin-top:4px }}
    th{{ background:#f1f5f9; padding:8px 10px; text-align:left; font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.5px; border-bottom:2px solid #e2e8f0; color:#475569 }}
    tr:nth-child(even) td{{ background:#f8fafc }}
    .footer{{ margin-top:40px; padding-top:16px; border-top:1px solid #e2e8f0; font-size:11px; color:#94a3b8; display:flex; justify-content:space-between }}
    @media print{{ .page{{ padding:20px 28px }} h2{{ margin-top:20px }} @page{{ margin:15mm }} }}
  </style>
</head>
<body>
<div class="page">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:28px;border-bottom:2px solid #e2e8f0;padding-bottom:20px">
    <div>
      <div style="font-size:11px;font-weight:700;color:#3b82f6;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">&#9729; CloudAudit</div>
      <h1>Cloud Resource Audit Report</h1>
      <div class="meta">
        Scan ID: <code style="font-size:11px">{scan_id}</code> &nbsp;&middot;&nbsp;
        Regions: {regions} &nbsp;&middot;&nbsp;
        Completed: {completed}
      </div>
    </div>
    <div style="text-align:right">
      <div style="font-size:11px;color:#64748b">Generated</div>
      <div style="font-size:12px;font-weight:600">{generated}</div>
    </div>
  </div>

  <h2>Executive Summary</h2>
  <div class="kpi-grid">
    <div class="kpi">
      <div class="kpi-val">{resource_count}</div>
      <div class="kpi-label">Resources Scanned</div>
    </div>
    <div class="kpi">
      <div class="kpi-val" style="color:{vio_pill_color}">{violation_count}</div>
      <div class="kpi-label">Violations Found</div>
    </div>
    <div class="kpi">
      <div class="kpi-val" style="color:#10b981">${total_savings_fmt}</div>
      <div class="kpi-label">Est. Monthly Savings</div>
    </div>
    <div class="kpi">
      <div class="kpi-val" style="color:#ef4444">${total_cost_fmt}</div>
      <div class="kpi-label">{waste_label}</div>
    </div>
  </div>

  <h3>Violations by Severity</h3>
  <div style="display:flex;gap:16px;margin-bottom:24px;flex-wrap:wrap">{sev_pills}</div>

  {cost_section}

  <h2>{rec_header}</h2>
  <table>
    <thead><tr>
      <th style="width:90px">Category</th>
      <th>Recommendation</th>
      <th style="width:80px">Severity</th>
      <th style="width:100px;text-align:right">Est. Savings</th>
      <th>Action</th>
    </tr></thead>
    <tbody>{rec_rows}</tbody>
  </table>

  <h2 style="margin-top:36px">{vio_header}</h2>
  <table>
    <thead><tr>
      <th style="width:90px">Rule</th>
      <th style="width:80px">Severity</th>
      <th style="width:70px">Type</th>
      <th style="width:160px">Resource ID</th>
      <th style="width:90px">Region</th>
      <th>Message</th>
    </tr></thead>
    <tbody>{vio_rows}</tbody>
  </table>

  <div class="footer">
    <span>CloudAudit &mdash; Cloud Resource Audit &amp; Cost Optimization Platform</span>
    <span>Generated {generated}</span>
  </div>
</div>
</body>
</html>""".format(
        scan_id_short=scan_id_short,
        scan_id=scan_id,
        regions=regions,
        completed=completed,
        generated=generated,
        resource_count=resource_count,
        violation_count=violation_count,
        vio_pill_color=vio_pill_color,
        total_savings_fmt="{:,.2f}".format(total_savings),
        total_cost_fmt="{:,.2f}".format(total_cost),
        waste_label=waste_label,
        sev_pills=sev_pills,
        cost_section=cost_section,
        rec_header=rec_header,
        rec_rows=rec_rows,
        vio_header=vio_violation_header,
        vio_rows=vio_rows,
    )
