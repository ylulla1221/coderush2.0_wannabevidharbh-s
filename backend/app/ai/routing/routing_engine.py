"""
CivicFlow AI Routing Engine — orchestrator.

Public API
----------
This module exposes exactly ONE callable to the rest of the system::

    from app.ai.routing import calculate_route

    result: dict = calculate_route(
        complaint_data=llm_result,
        duplicate_data=duplicate_result,
        priority_data=priority_result,
    )

Architecture
------------
The function follows a strict, linear decision pipeline:

    ┌──────────────────────────────────────┐
    │  1. Merge & validate inputs          │
    │     (Pydantic v2 model_validate)     │
    ├──────────────────────────────────────┤
    │  2. Determine department             │
    │     (CATEGORY_TO_DEPARTMENT lookup)  │
    ├──────────────────────────────────────┤
    │  3. Determine team                   │
    │     (CATEGORY_TO_TEAM lookup)        │
    ├──────────────────────────────────────┤
    │  4. Determine zone                   │
    │     (CATEGORY_TO_ZONE lookup)        │
    ├──────────────────────────────────────┤
    │  5. Determine SLA                    │
    │     (base SLA + priority override)   │
    ├──────────────────────────────────────┤
    │  6. Determine escalation             │
    │     (level, score, category, cluster)│
    ├──────────────────────────────────────┤
    │  7. Assemble routing_reason list     │
    ├──────────────────────────────────────┤
    │  8. Return RoutingResult.model_dump()│
    └──────────────────────────────────────┘

Design Principles
-----------------
- **Deterministic**: identical inputs always produce identical outputs.
- **No AI / no randomness**: every decision traces to a dict lookup or
  an integer / float comparison.
- **Defensive**: every dict access has a typed fallback; Pydantic
  validation is wrapped so the engine degrades gracefully instead of
  raising unhandled exceptions into the pipeline.
- **Auditable**: the ``routing_reason`` field in the result records each
  individual decision step so auditors can reproduce the decision.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from . import config, constants
from .exceptions import RoutingValidationError
from .jurisdiction import lookup_location
from .knowledge_base import get_fallback_route, lookup_category
from .models import RoutingInput, RoutingResult
from .planning_engine import get_department_plan

logger = logging.getLogger("civicflow.ai.routing")

# Routing Engine version — bump this when breaking changes are made to the
# routing pipeline so audit records can be traced to a specific engine.
_ROUTING_VERSION: str = "2.0.0"

# Ordered list of pipeline stage names used to build the provenance object.
_PIPELINE_STAGES: list[str] = [
    "Category Classification",
    "Routing Knowledge Base",
    "Jurisdiction Resolution",
    "Decision Engine",
    "Planning Engine",
]

# =============================================================================
# PRIVATE HELPERS
#
# Each helper resolves ONE routing dimension and appends a sentence to the
# shared ``reasons`` list. They are intentionally small, single-purpose
# functions to remain individually testable.
# =============================================================================


def _resolve_department(category: str | None, reasons: list[str]) -> str:
    """Map complaint category to its responsible government department.

    Performs a case-sensitive dict lookup against
    ``constants.CATEGORY_TO_DEPARTMENT``. Falls back to
    ``config.DEFAULT_DEPARTMENT`` when the category is absent or unknown.

    Args:
        category: Civic issue category string from the Vision LLM.
        reasons: Mutable list that receives an explanatory sentence.

    Returns:
        Name of the assigned department.
    """
    if category and category in constants.CATEGORY_TO_DEPARTMENT:
        department = constants.CATEGORY_TO_DEPARTMENT[category]
        reasons.append(
            f"Category '{category}' maps to '{department}'."
        )
    else:
        department = config.DEFAULT_DEPARTMENT
        reasons.append(
            f"Category '{category}' is unrecognised; "
            f"defaulting to '{department}'."
        )

    return department


def _resolve_team(category: str | None, reasons: list[str]) -> str:
    """Map complaint category to the specialist field team.

    Performs a case-sensitive dict lookup against
    ``constants.CATEGORY_TO_TEAM``. Falls back to
    ``config.DEFAULT_TEAM`` when the category is absent or unknown.

    Args:
        category: Civic issue category string from the Vision LLM.
        reasons: Mutable list that receives an explanatory sentence.

    Returns:
        Name of the assigned specialist team.
    """
    if category and category in constants.CATEGORY_TO_TEAM:
        team = constants.CATEGORY_TO_TEAM[category]
        reasons.append(
            f"Complaint assigned to '{team}'."
        )
    else:
        team = config.DEFAULT_TEAM
        reasons.append(
            f"No specialist team found for '{category}'; "
            f"defaulting to '{team}'."
        )

    return team


def _resolve_zone(category: str | None, reasons: list[str]) -> str:
    """Map complaint category to an administrative geographic zone.

    Performs a case-sensitive dict lookup against
    ``constants.CATEGORY_TO_ZONE``. Falls back to
    ``config.DEFAULT_ZONE`` when the category is absent or unknown.

    Args:
        category: Civic issue category string from the Vision LLM.
        reasons: Mutable list that receives an explanatory sentence.

    Returns:
        Zone identifier string (e.g. ``"Zone A"``).
    """
    if category and category in constants.CATEGORY_TO_ZONE:
        zone = constants.CATEGORY_TO_ZONE[category]
        reasons.append(
            f"Complaint routed to geographic '{zone}'."
        )
    else:
        zone = config.DEFAULT_ZONE
        reasons.append(
            f"No zone mapping found for '{category}'; "
            f"defaulting to '{zone}'."
        )

    return zone


def _resolve_sla(
    category: str | None,
    priority_level: str,
    reasons: list[str],
) -> int:
    """Calculate the final SLA commitment in hours.

    The algorithm uses two steps:

    1. **Base SLA**: looked up from ``constants.CATEGORY_TO_BASE_SLA``
       (or ``config.DEFAULT_SLA_HOURS`` if the category is absent).
    2. **Priority override**: maps the priority level to a stricter SLA
       from ``config`` (CRITICAL_PRIORITY_SLA, HIGH_PRIORITY_SLA, etc.).
       The override is applied only when it is *stricter* (fewer hours)
       than the base SLA, so a High-priority Garbage complaint gets the
       High override (12 h) rather than the base (48 h).

    The result is clamped between ``config.MIN_SLA_HOURS`` and
    ``config.MAX_SLA_HOURS``.

    Args:
        category: Civic issue category string from the Vision LLM.
        priority_level: Priority level string from the Priority Engine.
        reasons: Mutable list that receives explanatory sentences.

    Returns:
        Final SLA commitment in hours.
    """
    # Step 1 — base SLA from category
    if category and category in constants.CATEGORY_TO_BASE_SLA:
        base_sla = constants.CATEGORY_TO_BASE_SLA[category]
        reasons.append(
            f"Base SLA for '{category}' is {base_sla} hours."
        )
    else:
        base_sla = config.DEFAULT_SLA_HOURS
        reasons.append(
            f"No base SLA mapping for '{category}'; "
            f"using default {base_sla} hours."
        )

    # Step 2 — priority-level override
    _priority_sla_map: dict[str, int] = {
        "Critical": config.CRITICAL_PRIORITY_SLA,
        "High":     config.HIGH_PRIORITY_SLA,
        "Medium":   config.MEDIUM_PRIORITY_SLA,
        "Low":      config.LOW_PRIORITY_SLA,
    }
    priority_sla = _priority_sla_map.get(priority_level, config.DEFAULT_SLA_HOURS)

    if priority_sla < base_sla:
        reasons.append(
            f"'{priority_level}' priority overrides SLA to {priority_sla} hours "
            f"(stricter than base {base_sla} hours)."
        )
        effective_sla = priority_sla
    else:
        reasons.append(
            f"Base SLA ({base_sla} h) is already stricter than "
            f"'{priority_level}' priority SLA ({priority_sla} h); "
            "base SLA retained."
        )
        effective_sla = base_sla

    # Step 3 — hard clamp
    final_sla = max(config.MIN_SLA_HOURS, min(config.MAX_SLA_HOURS, effective_sla))

    if final_sla != effective_sla:
        reasons.append(
            f"SLA clamped to hard limit: {final_sla} hours."
        )

    return final_sla


def _resolve_escalation(
    priority_level: str,
    priority_score: float,
    category: str | None,
    cluster_size: int,
    reasons: list[str],
) -> bool:
    """Determine whether the complaint must be escalated.

    Escalation is triggered by **any** of the following (OR logic):

    1. ``priority_level`` is in ``constants.ESCALATION_PRIORITY_LEVELS``
       (``"Critical"`` or ``"High"``).
    2. ``priority_score >= config.ESCALATION_SCORE_THRESHOLD`` — numeric
       safety net for borderline High/Critical complaints.
    3. ``category`` is in ``constants.ALWAYS_ESCALATE_CATEGORIES``
       (life-threatening categories always escalate).
    4. ``cluster_size >= constants.ESCALATION_CLUSTER_THRESHOLD`` — high
       community impact signals systemic failure.

    Args:
        priority_level: Priority level string from the Priority Engine.
        priority_score: Numeric score from the Priority Engine.
        category: Civic issue category from the Vision LLM.
        cluster_size: Duplicate cluster size from Duplicate Detection.
        reasons: Mutable list that receives explanatory sentences.

    Returns:
        ``True`` if the complaint must be escalated; ``False`` otherwise.
    """
    escalate = False

    # Trigger 1 — priority level
    if priority_level in constants.ESCALATION_PRIORITY_LEVELS:
        escalate = True
        reasons.append(
            f"'{priority_level}' priority level triggers escalation."
        )

    # Trigger 2 — numeric score safety net
    if priority_score >= config.ESCALATION_SCORE_THRESHOLD:
        if not escalate:
            escalate = True
            reasons.append(
                f"Priority score {priority_score:.1f} exceeds escalation "
                f"threshold ({config.ESCALATION_SCORE_THRESHOLD:.1f})."
            )

    # Trigger 3 — always-escalate categories
    if category and category in constants.ALWAYS_ESCALATE_CATEGORIES:
        if not escalate:
            escalate = True
        reasons.append(
            f"Category '{category}' is classified as a public-safety "
            "hazard and always requires escalation."
        )

    # Trigger 4 — community impact / cluster size
    if cluster_size >= constants.ESCALATION_CLUSTER_THRESHOLD:
        if not escalate:
            escalate = True
        reasons.append(
            f"Cluster size {cluster_size} meets or exceeds the community "
            f"impact threshold ({constants.ESCALATION_CLUSTER_THRESHOLD} "
            "complaints); escalation required."
        )

    if not escalate:
        reasons.append(
            "No escalation criteria met; complaint enters standard queue."
        )

    return escalate


# =============================================================================
# PRIVATE — PHASE 1: KNOWLEDGE BASE METADATA
#
# Resolves department_code, description, default_explanation, and
# routing_status from the Routing Knowledge Base.  This is kept as a
# separate helper so it is independently testable and does not interfere
# with the existing _resolve_department / _resolve_team / _resolve_zone
# helpers which continue to work exactly as before.
# =============================================================================


def _resolve_kb_metadata(
    category: str | None,
    reasons: list[str],
) -> tuple[str | None, str | None, str | None, str]:
    """Look up Phase 1 Routing Knowledge Base metadata for a category.

    This helper is the ONLY function that reads from the knowledge base.
    All duplicate-decision, escalation, SLA, team, and zone logic is
    unchanged and still uses the flat lookup tables in constants.py.

    Args:
        category: Civic issue category string from the Vision LLM.
        reasons: Mutable list that receives an explanatory sentence.

    Returns:
        A tuple of
        (department_code, description, default_explanation, routing_status,
         alternative_department).
    """
    route = lookup_category(category)

    if route is not None:
        reasons.append(
            f"Knowledge Base matched category '{category}' to "
            f"department '{route.department}' "
            f"(code: {route.department_code})."
        )
        return (
            route.department_code,
            route.description,
            route.default_explanation,
            route.routing_status,
            route.alternative_department,
        )

    # Unknown category — return the safe fallback values
    fallback = get_fallback_route()
    reasons.append(
        f"Category '{category}' not found in Routing Knowledge Base; "
        "flagged for manual review."
    )
    return (
        fallback.department_code,
        fallback.description,
        fallback.default_explanation,
        fallback.routing_status,
        fallback.alternative_department,
    )


# =============================================================================
# PRIVATE — PHASE 2: JURISDICTION & GEOGRAPHY
#
# Resolves ward, zone_jurisdiction, municipal_body, and jurisdiction_found
# from the free-text location string extracted by the Vision LLM.
# This helper is the ONLY function that reads from jurisdiction.py/json.
# Department, team, SLA, and escalation logic are completely untouched.
# =============================================================================


def _resolve_jurisdiction(
    location: str | None,
    reasons: list[str],
) -> tuple[str | None, str | None, str | None, bool]:
    """Resolve a location string into jurisdiction metadata.

    Delegates to :func:`~.jurisdiction.lookup_location` which performs
    exact-then-substring matching against jurisdiction.json.

    Args:
        location: Free-text location string from the Vision LLM.
        reasons:  Mutable list that receives explanatory sentences.

    Returns:
        A tuple of (ward, zone_jurisdiction, municipal_body, jurisdiction_found).
    """
    result = lookup_location(location)

    if result.found:
        reasons.append(
            f"Location '{location}' resolved to {result.ward}, "
            f"{result.zone} ({result.municipal_body})."
        )
        return result.ward, result.zone, result.municipal_body, True

    reasons.append(
        f"Location '{location}' could not be mapped to a jurisdiction; "
        "manual review recommended."
    )
    return None, None, None, False


# =============================================================================
# PRIVATE — PHASE 3: CONFIDENCE SCORING
#
# Computes a simple, fully deterministic composite confidence score for the
# routing decision.  The score is based on three observable signals:
#   1. CategoryConfidence  — how confident the upstream LLM was in its category.
#   2. JurisdictionConfidence — whether the location was resolved.
#   3. DepartmentConfidence — whether a known department was matched.
# NO machine learning, NO randomness, NO external calls.
# =============================================================================


# Confidence thresholds and labels (Phase 3)
_CONF_VERY_HIGH: float = 0.95
_CONF_HIGH: float = 0.90
_CONF_MEDIUM: float = 0.80

# Human-review triggers: confidence below this level always requires review
_CONF_REVIEW_THRESHOLD: float = _CONF_MEDIUM


def _resolve_confidence(
    category_confidence: float,
    jurisdiction_found: bool,
    department_resolved: bool,
) -> tuple[float, float, str]:
    """Compute the routing confidence score and level.

    Equation::

        Confidence = 0.50 x CategoryConfidence
                   + 0.30 x JurisdictionConfidence
                   + 0.20 x DepartmentConfidence

    All component inputs are clamped to [0.0, 1.0] before use.
    The final result is also clamped to [0.0, 1.0].

    Args:
        category_confidence: LLM confidence in the category (0.0–1.0).
            Pass 1.0 when the upstream confidence is unavailable.
        jurisdiction_found:  True when Phase 2 resolved the location.
        department_resolved: True when a known department was matched.

    Returns:
        A tuple of (routing_confidence, routing_confidence_percentage,
        routing_confidence_level).
    """
    cat_conf = max(0.0, min(1.0, float(category_confidence)))
    jur_conf = 1.0 if jurisdiction_found else 0.0
    dep_conf = 1.0 if department_resolved else 0.0

    raw = (0.50 * cat_conf) + (0.30 * jur_conf) + (0.20 * dep_conf)
    confidence = max(0.0, min(1.0, raw))
    percentage = round(confidence * 100.0, 1)

    if confidence >= _CONF_VERY_HIGH:
        level = "Very High"
    elif confidence >= _CONF_HIGH:
        level = "High"
    elif confidence >= _CONF_MEDIUM:
        level = "Medium"
    else:
        level = "Low"

    return round(confidence, 3), percentage, level


# =============================================================================
# PRIVATE — PHASE 3: DECISION EXPLANATION
#
# Builds a structured, citizen-facing explanation list from observable facts.
# Entirely deterministic template logic — zero LLM involvement.
# =============================================================================


def _build_decision_explanation(
    category: str | None,
    department: str,
    ward: str | None,
    municipal_body: str | None,
    jurisdiction_found: bool,
    routing_confidence_level: str,
    human_review_required: bool,
) -> list[str]:
    """Build a structured decision explanation for the routing result.

    Each sentence is generated from a deterministic template based on
    observable routing facts. No randomness, no LLM, no external I/O.

    Args:
        category:                 Civic issue category (may be None).
        department:               Resolved department name.
        ward:                     Resolved ward, or None.
        municipal_body:           Resolved municipal corporation, or None.
        jurisdiction_found:       Whether jurisdiction was resolved.
        routing_confidence_level: Confidence band string.
        human_review_required:    Whether human review is triggered.

    Returns:
        Ordered list of human-readable explanation strings.
    """
    explanation: list[str] = []

    # Department sentence
    if category:
        explanation.append(
            f"Category '{category}' mapped to {department}."
        )
    else:
        explanation.append(
            f"Department determined from category: {department}."
        )

    # Jurisdiction sentences
    if jurisdiction_found and ward and municipal_body:
        explanation.append(f"Jurisdiction resolved to {ward}.")
        explanation.append(f"Municipal body: {municipal_body}.")
    else:
        explanation.append("Jurisdiction could not be resolved.")

    # Confidence sentence
    explanation.append(f"Routing confidence is {routing_confidence_level}.")

    # Review sentence
    if human_review_required:
        explanation.append("Manual review recommended.")

    return explanation


def _enrich_explanation_with_planning(
    explanation: list[str],
    workload_percentage: float | None,
    expected_response_hours: int | None,
    sla_risk: str,
) -> None:
    """Append Phase 4 operational planning sentences to the explanation list.

    Mutates ``explanation`` in-place so the Phase 3 sentences are preserved
    and the Phase 4 sentences are appended after them.

    Args:
        explanation:            Existing explanation list from Phase 3.
        workload_percentage:    Queue utilisation percentage, or ``None``.
        expected_response_hours: Expected response in hours, or ``None``.
        sla_risk:               SLA risk label (``"Low"`` / ``"Medium"`` /
                                ``"High"`` / ``"Unknown"``)
    """
    if workload_percentage is not None:
        explanation.append(
            f"Current workload is {workload_percentage:.0f}%."
        )
    if expected_response_hours is not None:
        explanation.append(
            f"Expected response within {expected_response_hours} hour"
            + ("s" if expected_response_hours != 1 else "") + "."
        )
    explanation.append(f"SLA risk is {sla_risk}.")


# =============================================================================
# PRIVATE — PHASE 5: GOVERNANCE & ACCOUNTABILITY
#
# Builds all governance metadata from facts already computed by the pipeline.
# Entirely deterministic — no LLM, no randomness, no external I/O.
# =============================================================================

# Governance version constant is defined at module level (_ROUTING_VERSION).


def _build_governance(
    decision_status: str,
    routing_confidence: float,
    human_review_required: bool,
    jurisdiction_found: bool,
    department_resolved: bool,
    complaint_data: dict[str, Any],
) -> tuple[str, str, dict, dict, dict]:
    """Produce all Phase 5 governance & accountability objects.

    Everything is derived deterministically from facts already computed by
    Phases 1–4.  No LLM, no ML, no external calls.

    Args:
        decision_status:       ``"automatic"`` or ``"human_review"``.
        routing_confidence:    Composite confidence score from Phase 3.
        human_review_required: Whether human review was triggered.
        jurisdiction_found:    Whether Phase 2 resolved the location.
        department_resolved:   Whether Phase 1 matched a department.
        complaint_data:        Original complaint dict (may contain
                               ``language`` or ``input_language`` key).

    Returns:
        A tuple of
        (governance_status, accountability_summary, provenance, audit,
         fairness_review).
    """
    # 1. Governance status
    governance_status = "governed" if decision_status == "automatic" else "requires_review"

    # 2. Accountability summary (deterministic templates)
    if decision_status == "automatic":
        accountability_summary = (
            "The complaint was routed automatically using category "
            "classification, jurisdiction lookup, and routing knowledge base. "
            "No human override was required."
        )
    else:
        parts: list[str] = []
        if not department_resolved:
            parts.append("the category could not be mapped to a department")
        if not jurisdiction_found:
            parts.append("the jurisdiction could not be resolved")
        if not parts:
            parts.append("routing confidence was below the required threshold")
        reason_str = " and ".join(parts)
        accountability_summary = (
            f"The complaint requires human review because {reason_str}."
        )

    # 3. Provenance
    provenance: dict[str, Any] = {
        "pipeline": list(_PIPELINE_STAGES),
        "routing_version": _ROUTING_VERSION,
    }

    # 4. Audit snapshot
    audit: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "routing_version": _ROUTING_VERSION,
        "decision_status": decision_status,
        "routing_confidence": routing_confidence,
    }

    # 5. Fairness review
    # Language information is read from the upstream complaint payload if
    # present; no language detection is performed here.
    translation_used: bool = bool(
        complaint_data.get("translation_used")
        or complaint_data.get("translated")
    )
    input_language: str = str(
        complaint_data.get("input_language")
        or complaint_data.get("language")
        or "Unknown"
    )
    fairness_notes = (
        "Routing completed using deterministic rules."
        if not human_review_required
        else "Manual review required; fairness of routing cannot be automatically guaranteed."
    )
    fairness_review: dict[str, Any] = {
        "translation_used": translation_used,
        "input_language": input_language,
        "jurisdiction_found": jurisdiction_found,
        "manual_review_required": human_review_required,
        "notes": fairness_notes,
    }

    return governance_status, accountability_summary, provenance, audit, fairness_review

# =============================================================================
# FALLBACK RESULT
#
# Used when Pydantic validation fails so the pipeline can continue
# instead of crashing.  The fallback is logged at ERROR level.
# =============================================================================

def _build_fallback_result(exc: Exception) -> dict[str, Any]:
    """Build a safe fallback RoutingResult after a validation failure.

    Args:
        exc: The exception that caused the fallback.

    Returns:
        Dictionary representation of a default RoutingResult.
    """
    kb_fallback = get_fallback_route()
    return RoutingResult(
        department=config.DEFAULT_DEPARTMENT,
        team=config.DEFAULT_TEAM,
        zone=config.DEFAULT_ZONE,
        sla_hours=config.DEFAULT_SLA_HOURS,
        requires_escalation=False,
        routing_reason=[
            "Input validation failed; fallback routing applied.",
            f"Cause: {exc}",
        ],
        # Phase 1 — KB fields
        department_code=kb_fallback.department_code,
        description=kb_fallback.description,
        default_explanation=kb_fallback.default_explanation,
        routing_status=kb_fallback.routing_status,
        # Phase 2 — Jurisdiction fields (unknown on validation failure)
        ward=None,
        zone_jurisdiction=None,
        municipal_body=None,
        jurisdiction_found=False,
        # Phase 3 — Decision Engine fields
        routing_confidence=0.0,
        routing_confidence_percentage=0.0,
        routing_confidence_level="Low",
        human_review_required=True,
        decision_status="human_review",
        alternative_department=kb_fallback.alternative_department,
        decision_explanation=[
            "Input validation failed; routing could not be determined.",
            f"Cause: {exc}",
            "Manual review required.",
        ],
        # Phase 4 — Operational Planning fields (unknown on validation failure)
        expected_response_hours=None,
        current_workload=None,
        queue_capacity=None,
        workload_percentage=None,
        sla_risk="Unknown",
        escalation_chain=[],
        # Phase 5 — Governance & Accountability fields
        governance_status="requires_review",
        accountability_summary=(
            "The complaint requires human review because input validation failed."
        ),
        human_override_allowed=True,
        human_override_reason=None,
        human_override_timestamp=None,
        human_override_by=None,
        provenance={
            "pipeline": list(_PIPELINE_STAGES),
            "routing_version": _ROUTING_VERSION,
        },
        audit={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "routing_version": _ROUTING_VERSION,
            "decision_status": "human_review",
            "routing_confidence": 0.0,
        },
        fairness_review={
            "translation_used": False,
            "input_language": "Unknown",
            "jurisdiction_found": False,
            "manual_review_required": True,
            "notes": "Manual review required; fairness of routing cannot be automatically guaranteed.",
        },
    ).model_dump()


# =============================================================================
# PUBLIC API
# =============================================================================


def calculate_route(
    complaint_data: dict[str, Any],
    duplicate_data: dict[str, Any],
    priority_data: dict[str, Any],
) -> dict[str, Any]:
    """Route a civic complaint to the correct department, team, and zone.

    This is the **only** public function exposed by the routing module.
    All other functions in this file are private helpers.

    The function is fully deterministic: the same inputs always produce
    the same output with zero randomness, no AI, and no external I/O.

    Pipeline:

        complaint_data + duplicate_data + priority_data
                ↓
            RoutingInput (Pydantic validation)
                ↓
            _resolve_department()
                ↓
            _resolve_team()
                ↓
            _resolve_zone()
                ↓
            _resolve_sla()
                ↓
            _resolve_escalation()
                ↓
            RoutingResult.model_dump()

    Args:
        complaint_data: Structured complaint dict from the Vision LLM.
            Expected keys: ``category``, ``location``.
        duplicate_data: Result dict from the Duplicate Detection module.
            Expected keys: ``is_duplicate``, ``cluster_size``.
        priority_data: Result dict from the Priority Engine.
            Expected keys: ``priority_level``, ``priority_score``.

    Returns:
        A JSON-serialisable dictionary matching the ``RoutingResult``
        schema::

            {
                "department":         str,
                "team":               str,
                "zone":               str,
                "sla_hours":          int,
                "requires_escalation": bool,
                "routing_reason":     list[str],
            }

    Raises:
        RoutingValidationError: Logged internally; the function degrades
            to a safe fallback result rather than propagating the exception
            up to the pipeline.
    """
    logger.info("=" * 80)
    logger.info("Starting Routing Engine")

    # ------------------------------------------------------------------
    # Step 1 — merge and validate inputs
    # ------------------------------------------------------------------

    combined: dict[str, Any] = {
        "category":      complaint_data.get("category"),
        "location":      complaint_data.get("location"),
        "priority_level": priority_data.get("priority_level", "Medium"),
        "priority_score": priority_data.get("priority_score", 40.0),
        "cluster_size":  duplicate_data.get("cluster_size", 1),
        "is_duplicate":  duplicate_data.get("is_duplicate", False),
    }

    logger.debug("Merged routing input: %s", combined)

    try:
        validated = RoutingInput.model_validate(combined)
    except Exception as exc:
        err = RoutingValidationError(str(exc))
        logger.error(
            "Routing Engine validation failed: %s", err.message
        )
        return _build_fallback_result(err)

    logger.info(
        "Routing | Category=%s | Priority=%s (%.1f) | Cluster=%d",
        validated.category,
        validated.priority_level,
        validated.priority_score,
        validated.cluster_size,
    )

    # ------------------------------------------------------------------
    # Shared reasons accumulator — passed by reference to each helper
    # ------------------------------------------------------------------

    reasons: list[str] = []

    # ------------------------------------------------------------------
    # Step 2 — department
    # ------------------------------------------------------------------

    department = _resolve_department(validated.category, reasons)

    # ------------------------------------------------------------------
    # Step 3 — team
    # ------------------------------------------------------------------

    team = _resolve_team(validated.category, reasons)

    # ------------------------------------------------------------------
    # Step 4 — zone
    # ------------------------------------------------------------------

    zone = _resolve_zone(validated.category, reasons)

    # ------------------------------------------------------------------
    # Step 5 — SLA
    # ------------------------------------------------------------------

    sla_hours = _resolve_sla(validated.category, validated.priority_level, reasons)

    # ------------------------------------------------------------------
    # Step 6 — escalation
    # ------------------------------------------------------------------

    requires_escalation = _resolve_escalation(
        priority_level=validated.priority_level,
        priority_score=validated.priority_score,
        category=validated.category,
        cluster_size=validated.cluster_size,
        reasons=reasons,
    )

    # ------------------------------------------------------------------
    # Step 7 — Phase 1: Routing Knowledge Base metadata
    # ------------------------------------------------------------------

    dept_code, kb_description, kb_explanation, routing_status, alt_dept = _resolve_kb_metadata(
        validated.category, reasons
    )

    # Determine whether a known department was matched (for Phase 3)
    department_resolved: bool = routing_status == "success"

    # ------------------------------------------------------------------
    # Step 8 — Phase 2: Jurisdiction & Geography
    # ------------------------------------------------------------------

    ward, zone_jurisdiction, municipal_body, jurisdiction_found = _resolve_jurisdiction(
        validated.location, reasons
    )

    # ------------------------------------------------------------------
    # Step 9 — Phase 3: Routing Confidence
    # ------------------------------------------------------------------

    # complaint_data may carry an upstream LLM confidence (0.0–1.0).
    # Fall back to 1.0 when absent so confidence is not unfairly penalised.
    category_confidence: float = float(
        complaint_data.get("confidence", 1.0) or 1.0
    )
    category_confidence = max(0.0, min(1.0, category_confidence))

    routing_confidence, routing_confidence_pct, routing_confidence_level = (
        _resolve_confidence(
            category_confidence=category_confidence,
            jurisdiction_found=jurisdiction_found,
            department_resolved=department_resolved,
        )
    )

    # ------------------------------------------------------------------
    # Step 10 — Phase 3: Human Review & Decision Status
    # ------------------------------------------------------------------

    human_review_required: bool = (
        routing_confidence < _CONF_REVIEW_THRESHOLD
        or not department_resolved
        or not jurisdiction_found
    )
    decision_status: str = "human_review" if human_review_required else "automatic"

    # ------------------------------------------------------------------
    # Step 11 — Phase 3: Decision Explanation
    # ------------------------------------------------------------------

    decision_explanation = _build_decision_explanation(
        category=validated.category,
        department=department,
        ward=ward,
        municipal_body=municipal_body,
        jurisdiction_found=jurisdiction_found,
        routing_confidence_level=routing_confidence_level,
        human_review_required=human_review_required,
    )

    # ------------------------------------------------------------------
    # Step 12 — Phase 4: Operational Planning
    # ------------------------------------------------------------------

    plan = get_department_plan(department)

    # Extend the decision explanation with planning sentences
    _enrich_explanation_with_planning(
        explanation=decision_explanation,
        workload_percentage=plan.workload_percentage,
        expected_response_hours=plan.expected_response_hours,
        sla_risk=plan.sla_risk,
    )

    # ------------------------------------------------------------------
    # Step 13 — Phase 5: Governance & Accountability
    # ------------------------------------------------------------------

    (
        governance_status,
        accountability_summary,
        provenance,
        audit,
        fairness_review,
    ) = _build_governance(
        decision_status=decision_status,
        routing_confidence=routing_confidence,
        human_review_required=human_review_required,
        jurisdiction_found=jurisdiction_found,
        department_resolved=department_resolved,
        complaint_data=complaint_data,
    )

    # ------------------------------------------------------------------
    # Step 14 — assemble result
    # ------------------------------------------------------------------

    result = RoutingResult(
        department=department,
        team=team,
        zone=zone,
        sla_hours=sla_hours,
        requires_escalation=requires_escalation,
        routing_reason=reasons,
        # Phase 1 — KB fields
        department_code=dept_code,
        description=kb_description,
        default_explanation=kb_explanation,
        routing_status=routing_status,
        # Phase 2 — Jurisdiction fields
        ward=ward,
        zone_jurisdiction=zone_jurisdiction,
        municipal_body=municipal_body,
        jurisdiction_found=jurisdiction_found,
        # Phase 3 — Decision Engine fields
        routing_confidence=routing_confidence,
        routing_confidence_percentage=routing_confidence_pct,
        routing_confidence_level=routing_confidence_level,
        human_review_required=human_review_required,
        decision_status=decision_status,
        alternative_department=alt_dept,
        decision_explanation=decision_explanation,
        # Phase 4 — Operational Planning fields
        expected_response_hours=plan.expected_response_hours,
        current_workload=plan.current_workload,
        queue_capacity=plan.queue_capacity,
        workload_percentage=plan.workload_percentage,
        sla_risk=plan.sla_risk,
        escalation_chain=plan.escalation_chain,
        # Phase 5 — Governance & Accountability fields
        governance_status=governance_status,
        accountability_summary=accountability_summary,
        human_override_allowed=True,
        human_override_reason=None,
        human_override_timestamp=None,
        human_override_by=None,
        provenance=provenance,
        audit=audit,
        fairness_review=fairness_review,
    )

    logger.info(
        "Routing completed | Department=%s (%s) | Team=%s | "
        "Zone=%s | SLA=%dh | Escalation=%s | Status=%s | "
        "Ward=%s | MunicipalBody=%s | JurisdictionFound=%s | "
        "Confidence=%.3f (%s) | HumanReview=%s | DecisionStatus=%s | "
        "Workload=%.1f%% | SLARisk=%s | GovernanceStatus=%s",
        result.department,
        result.department_code,
        result.team,
        result.zone,
        result.sla_hours,
        result.requires_escalation,
        result.routing_status,
        result.ward,
        result.municipal_body,
        result.jurisdiction_found,
        result.routing_confidence,
        result.routing_confidence_level,
        result.human_review_required,
        result.decision_status,
        result.workload_percentage if result.workload_percentage is not None else 0.0,
        result.sla_risk,
        result.governance_status,
    )
    logger.info("=" * 80)

    return result.model_dump()
