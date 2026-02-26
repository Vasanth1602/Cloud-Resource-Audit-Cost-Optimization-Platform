from __future__ import annotations

from typing import Any

# Severity → base score mapping
_SEVERITY_SCORE: dict[str, float] = {
    "CRITICAL": 40.0,
    "HIGH": 25.0,
    "MEDIUM": 15.0,
    "LOW": 5.0,
    "INFO": 1.0,
}


def compute_risk_score(violations: list[dict[str, Any]]) -> float:
    """
    Compute a risk score (0–100) for a resource based on its violations.
    Multiple violations stack additively, capped at 100.

    Score thresholds for UI display:
      0–25   → LOW risk (green)
      26–50  → MEDIUM risk (yellow)
      51–75  → HIGH risk (orange)
      76–100 → CRITICAL risk (red)
    """
    if not violations:
        return 0.0

    score = sum(_SEVERITY_SCORE.get(v.get("severity", "INFO"), 1.0) for v in violations)
    return round(min(score, 100.0), 1)


def risk_label(score: float) -> str:
    if score >= 76:
        return "CRITICAL"
    elif score >= 51:
        return "HIGH"
    elif score >= 26:
        return "MEDIUM"
    elif score > 0:
        return "LOW"
    return "CLEAN"
