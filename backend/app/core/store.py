"""
In-memory data store with JSON file persistence.
Data survives backend restarts — no database required.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
_lock = threading.Lock()

# Persist data next to this file in the backend directory
_DATA_FILE = Path(__file__).parent.parent.parent.parent / "scan_data.json"

# ── In-memory stores ───────────────────────────────────────────
scan_sessions: dict[str, dict[str, Any]] = {}
scan_resources: dict[str, list[dict[str, Any]]] = {}
scan_violations: dict[str, list[dict[str, Any]]] = {}
scan_costs: dict[str, list[dict[str, Any]]] = {}
remediation_logs: list[dict[str, Any]] = []


def _load() -> None:
    """Load persisted data from JSON file on startup."""
    global scan_sessions, scan_resources, scan_violations, scan_costs, remediation_logs
    if not _DATA_FILE.exists():
        return
    try:
        with open(_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        scan_sessions.update(data.get("scan_sessions", {}))
        scan_resources.update(data.get("scan_resources", {}))
        scan_violations.update(data.get("scan_violations", {}))
        scan_costs.update(data.get("scan_costs", {}))
        remediation_logs.extend(data.get("remediation_logs", []))
        logger.info(f"Loaded {len(scan_sessions)} scan(s) from {_DATA_FILE}")
    except Exception as e:
        logger.warning(f"Could not load scan data: {e}")


def save() -> None:
    """Persist current data to JSON file."""
    with _lock:
        try:
            data = {
                "saved_at": datetime.utcnow().isoformat(),
                "scan_sessions": scan_sessions,
                "scan_resources": scan_resources,
                "scan_violations": scan_violations,
                "scan_costs": scan_costs,
                "remediation_logs": remediation_logs,
            }
            with open(_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, default=str)
        except Exception as e:
            logger.warning(f"Could not save scan data: {e}")


def clear_all() -> None:
    """Clear everything including the saved file."""
    with _lock:
        scan_sessions.clear()
        scan_resources.clear()
        scan_violations.clear()
        scan_costs.clear()
        remediation_logs.clear()
        if _DATA_FILE.exists():
            _DATA_FILE.unlink()


# Load persisted data on import
_load()
