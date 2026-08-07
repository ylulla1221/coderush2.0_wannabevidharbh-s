"""
Routing Knowledge Base loader for the CivicFlow AI Routing Engine.

Phase 1 — Configurable Routing Knowledge Base
----------------------------------------------
This module replaces the scattered flat dictionaries in constants.py with a
single, unified routing knowledge base (knowledge_base.json).  Every civic
complaint category is represented by one self-contained record that contains
all the metadata the routing engine needs.

Public API
----------
lookup_category(category) -> CategoryRoute | None
    Returns a populated CategoryRoute dataclass for a known category, or
    None for an unrecognised one.  Callers are responsible for safe
    fallback handling.

get_fallback_route() -> CategoryRoute
    Returns a safe, human-review CategoryRoute used when a category is
    not found in the knowledge base.

ROUTING_KB: dict[str, CategoryRoute]
    The fully parsed knowledge base, keyed by category name.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("civicflow.ai.routing.knowledge_base")

# =============================================================================
# KNOWLEDGE BASE PATH
# =============================================================================

_KB_PATH: Path = Path(__file__).resolve().parent / "knowledge_base.json"


# =============================================================================
# DATA CONTRACT
# =============================================================================


@dataclass(frozen=True)
class CategoryRoute:
    """Immutable routing record for a single civic complaint category.

    Attributes:
        category:            The civic issue category this record covers.
        department:          Human-readable department name.
        department_code:     Short alphanumeric code for the department.
        sla_hours:           Default SLA commitment in hours.
        description:         What the department does (for UI / notifications).
        default_explanation: Citizen-facing explanation of why the complaint
                             was routed here.
        routing_status:      ``"success"`` for known categories;
                             ``"manual_review"`` for the fallback record.
    """

    category: str
    department: str | None
    department_code: str | None
    sla_hours: int
    description: str
    default_explanation: str
    routing_status: str = "success"
    # Phase 3 — alternative department (may be null in JSON)
    alternative_department: str | None = None


# =============================================================================
# LOADER
# =============================================================================


def _load_knowledge_base(path: Path) -> dict[str, CategoryRoute]:
    """Parse knowledge_base.json and return a fully typed dict.

    Args:
        path: Absolute path to the JSON knowledge base file.

    Returns:
        Dictionary keyed by category name; values are CategoryRoute objects.

    Raises:
        FileNotFoundError: If the JSON file cannot be found.
        json.JSONDecodeError: If the file is not valid JSON.
        KeyError: If a required field is missing from a record.
    """
    with path.open(encoding="utf-8") as fh:
        raw: dict = json.load(fh)

    result: dict[str, CategoryRoute] = {}
    for category, record in raw.items():
        result[category] = CategoryRoute(
            category=category,
            department=record["department"],
            department_code=record["department_code"],
            sla_hours=int(record["sla_hours"]),
            description=record["description"],
            default_explanation=record["default_explanation"],
            routing_status="success",
            # Phase 3 — optional; defaults to None if key absent
            alternative_department=record.get("alternative_department"),
        )

    logger.info(
        "Routing Knowledge Base loaded: %d categories from '%s'.",
        len(result),
        path.name,
    )
    return result


# =============================================================================
# SINGLETON — loaded once at import time
# =============================================================================

try:
    ROUTING_KB: dict[str, CategoryRoute] = _load_knowledge_base(_KB_PATH)
except Exception as exc:  # noqa: BLE001
    # If the JSON file is missing or malformed the engine must not crash;
    # it will fall back to per-lookup None returns handled by the caller.
    logger.error(
        "Failed to load Routing Knowledge Base from '%s': %s. "
        "All lookups will return the fallback route.",
        _KB_PATH,
        exc,
    )
    ROUTING_KB = {}


# =============================================================================
# FALLBACK RECORD
# =============================================================================

_FALLBACK_ROUTE = CategoryRoute(
    category="Unknown",
    department=None,
    department_code=None,
    sla_hours=72,
    description="Category not recognised by the Routing Knowledge Base.",
    default_explanation=(
        "The complaint category was not recognised. "
        "A human reviewer will assess and route this complaint manually."
    ),
    routing_status="manual_review",
    alternative_department=None,
)


# =============================================================================
# PUBLIC API
# =============================================================================


def lookup_category(category: str | None) -> CategoryRoute | None:
    """Look up a category in the Routing Knowledge Base.

    Args:
        category: Civic issue category string (case-sensitive).
            ``None`` or empty string returns ``None``.

    Returns:
        A ``CategoryRoute`` if the category is known, ``None`` otherwise.
    """
    if not category:
        return None
    return ROUTING_KB.get(category)


def get_fallback_route() -> CategoryRoute:
    """Return the safe fallback route for unrecognised categories.

    Returns:
        A ``CategoryRoute`` with ``routing_status="manual_review"``
        and ``department=None``.
    """
    return _FALLBACK_ROUTE
