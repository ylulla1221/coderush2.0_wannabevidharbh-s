"""
Operational Planning Engine for the CivicFlow AI Routing Engine.

Phase 4 — Operational Planning Engine
--------------------------------------
This module loads planning_rules.json once at import time and exposes a
single public function for producing an operational plan for any department.

Architecture mirrors Phase 1 (knowledge_base.py) and Phase 2 (jurisdiction.py):
  - JSON is the single source of truth; no hardcoded planning values in code.
  - Module-level singleton — parsed once, cached for the process lifetime.
  - All lookups degrade gracefully — callers always receive a valid plan.

Workload model
--------------
``workload_percentage`` = (current_workload / queue_capacity) × 100, clamped
to [0, 100].

SLA risk thresholds
-------------------
0–50%   → Low
50–80%  → Medium
>80%    → High
Unknown → "Unknown" (when the department is not in the config)

Public API
----------
get_department_plan(department: str | None) -> DepartmentPlan
    Always returns a DepartmentPlan; never raises.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("civicflow.ai.routing.planning_engine")

# =============================================================================
# PLANNING RULES PATH
# =============================================================================

_PLANNING_PATH: Path = Path(__file__).resolve().parent / "planning_rules.json"

# =============================================================================
# SLA RISK THRESHOLDS
# =============================================================================

_SLA_RISK_MEDIUM_THRESHOLD: float = 50.0
_SLA_RISK_HIGH_THRESHOLD: float = 80.0

# =============================================================================
# DATA CONTRACT
# =============================================================================


@dataclass(frozen=True)
class DepartmentPlan:
    """Immutable operational plan for one department.

    Attributes:
        sla_hours:              SLA commitment in hours from planning config.
        expected_response_hours: Expected resolution time in hours (MVP = sla_hours).
        current_workload:        Number of active complaints in the department queue.
        queue_capacity:          Maximum queue capacity for the department.
        workload_percentage:     (current_workload / queue_capacity) × 100, clamped
                                 to [0, 100].  ``None`` when department is unknown.
        sla_risk:               ``"Low"`` | ``"Medium"`` | ``"High"`` | ``"Unknown"``.
        escalation_chain:       Ordered list of escalation roles for this department.
        found:                  ``True`` when the department was found in config.
    """

    sla_hours: int | None
    expected_response_hours: int | None
    current_workload: int | None
    queue_capacity: int | None
    workload_percentage: float | None
    sla_risk: str
    escalation_chain: list[str]
    found: bool


# =============================================================================
# FALLBACK
# =============================================================================

_FALLBACK_PLAN = DepartmentPlan(
    sla_hours=None,
    expected_response_hours=None,
    current_workload=None,
    queue_capacity=None,
    workload_percentage=None,
    sla_risk="Unknown",
    escalation_chain=[],
    found=False,
)


# =============================================================================
# LOADER
# =============================================================================


def _compute_workload_percentage(current: int, capacity: int) -> float:
    """Compute clamped workload percentage.

    Args:
        current:  Active complaints in queue.
        capacity: Maximum queue capacity.

    Returns:
        Percentage in [0.0, 100.0].
    """
    if capacity <= 0:
        return 100.0
    raw = (current / capacity) * 100.0
    return round(max(0.0, min(100.0, raw)), 1)


def _compute_sla_risk(workload_pct: float) -> str:
    """Derive SLA risk label from workload percentage.

    Rules:
        0–50%   → ``"Low"``
        50–80%  → ``"Medium"``
        >80%    → ``"High"``

    Args:
        workload_pct: Workload as a percentage [0, 100].

    Returns:
        One of ``"Low"``, ``"Medium"``, or ``"High"``.
    """
    if workload_pct > _SLA_RISK_HIGH_THRESHOLD:
        return "High"
    if workload_pct > _SLA_RISK_MEDIUM_THRESHOLD:
        return "Medium"
    return "Low"


def _load_planning_rules(path: Path) -> dict[str, DepartmentPlan]:
    """Parse planning_rules.json and return a fully typed lookup dict.

    Args:
        path: Absolute path to the JSON planning rules file.

    Returns:
        Dictionary keyed by department name; values are ``DepartmentPlan``
        objects with pre-computed ``workload_percentage`` and ``sla_risk``.

    Raises:
        FileNotFoundError: If the JSON file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
        KeyError: If a required field is missing from a record.
    """
    with path.open(encoding="utf-8") as fh:
        raw: dict = json.load(fh)

    result: dict[str, DepartmentPlan] = {}
    for department, record in raw.items():
        sla_hours = int(record["default_sla_hours"])
        current = int(record["current_workload"])
        capacity = int(record["queue_capacity"])
        workload_pct = _compute_workload_percentage(current, capacity)
        sla_risk = _compute_sla_risk(workload_pct)

        result[department] = DepartmentPlan(
            sla_hours=sla_hours,
            expected_response_hours=sla_hours,   # MVP: equal to SLA
            current_workload=current,
            queue_capacity=capacity,
            workload_percentage=workload_pct,
            sla_risk=sla_risk,
            escalation_chain=list(record.get("escalation_chain", [])),
            found=True,
        )

    logger.info(
        "Planning Rules loaded: %d departments from '%s'.",
        len(result),
        path.name,
    )
    return result


# =============================================================================
# SINGLETON — loaded once at import time
# =============================================================================

try:
    _PLANNING_DB: dict[str, DepartmentPlan] = _load_planning_rules(_PLANNING_PATH)
except Exception as exc:  # noqa: BLE001
    logger.error(
        "Failed to load Planning Rules from '%s': %s. "
        "All lookups will return the fallback plan.",
        _PLANNING_PATH,
        exc,
    )
    _PLANNING_DB = {}


# =============================================================================
# PUBLIC API
# =============================================================================


def get_department_plan(department: str | None) -> DepartmentPlan:
    """Return the operational plan for a department.

    Args:
        department: Department name (must match a key in planning_rules.json).
            ``None`` or empty string immediately returns the fallback plan.

    Returns:
        A :class:`DepartmentPlan`; never raises.
    """
    if not department or not _PLANNING_DB:
        return _FALLBACK_PLAN

    plan = _PLANNING_DB.get(department)
    if plan is None:
        logger.debug(
            "Planning Engine: no plan found for department '%s'; using fallback.",
            department,
        )
        return _FALLBACK_PLAN

    logger.debug(
        "Planning Engine: department '%s' | workload=%.1f%% | sla_risk=%s.",
        department,
        plan.workload_percentage,
        plan.sla_risk,
    )
    return plan
