"""
Jurisdiction loader for the CivicFlow AI Routing Engine.

Phase 2 — Jurisdiction & Geography Engine
------------------------------------------
This module loads jurisdiction.json once at import time and exposes a
single public function for resolving a free-text location string into
structured geographic metadata (ward, zone, municipal body).

Architecture mirrors knowledge_base.py from Phase 1:
  - JSON is the single source of truth; no hardcoded locations in code.
  - Module is loaded once and cached as a module-level singleton.
  - All lookups degrade gracefully — callers always receive a valid dict.

Lookup Strategy
---------------
1. Exact match  — normalised input matches a key directly.
2. Substring match — a known key is contained inside the normalised input
   (e.g. "VIT Pune Gate 3" → matches key "vit pune gate 3", then "vit pune").
   The longest matching key wins to minimise false positives.
3. Fallback — returns a safe ``found=False`` result instead of raising.

Public API
----------
lookup_location(location: str | None) -> JurisdictionResult
    Always returns a JurisdictionResult; never raises.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("civicflow.ai.routing.jurisdiction")

# =============================================================================
# JURISDICTION FILE PATH
# =============================================================================

_JURISDICTION_PATH: Path = Path(__file__).resolve().parent / "jurisdiction.json"


# =============================================================================
# DATA CONTRACT
# =============================================================================


@dataclass(frozen=True)
class JurisdictionResult:
    """Immutable result of a jurisdiction lookup.

    Attributes:
        ward:           Municipal ward identifier, or ``None`` if unknown.
        zone:           Administrative zone identifier, or ``None`` if unknown.
        municipal_body: Name of the governing municipal corporation,
                        or ``None`` if unknown.
        found:          ``True`` when the location was resolved; ``False``
                        for the fallback result.
    """

    ward: str | None
    zone: str | None
    municipal_body: str | None
    found: bool


# =============================================================================
# FALLBACK
# =============================================================================

_FALLBACK = JurisdictionResult(
    ward=None,
    zone=None,
    municipal_body=None,
    found=False,
)


# =============================================================================
# LOADER
# =============================================================================


def _load_jurisdiction(path: Path) -> dict[str, JurisdictionResult]:
    """Parse jurisdiction.json and return a normalised lookup dict.

    Keys in the returned dict are already lowercase-stripped so all
    comparisons in lookup_location() can use plain equality.

    Args:
        path: Absolute path to the jurisdiction JSON file.

    Returns:
        Dictionary keyed by normalised location string.

    Raises:
        FileNotFoundError: If the JSON file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
        KeyError: If a required field is missing from a record.
    """
    with path.open(encoding="utf-8") as fh:
        raw: dict = json.load(fh)

    result: dict[str, JurisdictionResult] = {}
    for key, record in raw.items():
        # Skip metadata keys that start with underscore
        if key.startswith("_"):
            continue
        normalised_key = key.strip().lower()
        result[normalised_key] = JurisdictionResult(
            ward=record["ward"],
            zone=record["zone"],
            municipal_body=record["municipal_body"],
            found=True,
        )

    logger.info(
        "Jurisdiction database loaded: %d locations from '%s'.",
        len(result),
        path.name,
    )
    return result


# =============================================================================
# SINGLETON — loaded once at import time
# =============================================================================

try:
    _JURISDICTION_DB: dict[str, JurisdictionResult] = _load_jurisdiction(
        _JURISDICTION_PATH
    )
except Exception as exc:  # noqa: BLE001
    logger.error(
        "Failed to load jurisdiction database from '%s': %s. "
        "All lookups will return the fallback result.",
        _JURISDICTION_PATH,
        exc,
    )
    _JURISDICTION_DB = {}


# =============================================================================
# PUBLIC API
# =============================================================================


def lookup_location(location: str | None) -> JurisdictionResult:
    """Resolve a free-text location string into jurisdiction metadata.

    Lookup strategy (in order):
    1. Exact normalised match.
    2. Longest substring match — finds the longest known key that appears
       inside the normalised location string (handles "VIT Pune Gate 3"
       matching the "vit pune gate 3" key, etc.).
    3. Fallback with ``found=False``.

    Args:
        location: Free-text location string from the Vision LLM.
            ``None`` or empty string immediately returns the fallback.

    Returns:
        A :class:`JurisdictionResult`; never raises.
    """
    if not location or not _JURISDICTION_DB:
        return _FALLBACK

    normalised = location.strip().lower()

    # 1. Exact match
    if normalised in _JURISDICTION_DB:
        logger.debug("Jurisdiction: exact match for '%s'.", normalised)
        return _JURISDICTION_DB[normalised]

    # 2. Longest substring match
    best_key: str | None = None
    for key in _JURISDICTION_DB:
        if key in normalised or normalised in key:
            if best_key is None or len(key) > len(best_key):
                best_key = key

    if best_key is not None:
        logger.debug(
            "Jurisdiction: substring match '%s' → '%s'.",
            normalised,
            best_key,
        )
        return _JURISDICTION_DB[best_key]

    # 3. Fallback
    logger.debug(
        "Jurisdiction: no match found for '%s'; returning fallback.",
        normalised,
    )
    return _FALLBACK
