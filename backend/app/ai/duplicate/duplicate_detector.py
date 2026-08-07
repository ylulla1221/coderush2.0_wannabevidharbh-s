"""
Duplicate detection orchestrator for CivicFlow AI.

This module is the SOLE public interface for duplicate detection.
External modules call ONLY `find_duplicate_complaint()` — the
embedder, vector store, and similarity logic are internal concerns.

Pipeline:
    Structured Complaint JSON (from LLM module)
        ↓
    Summary Extraction
        ↓
    Embedding Generation          (embedder.py)
        ↓
    Vector Database Search        (vector_store.py)
        ↓
    Similarity Calculation        (this file)
        ↓
    Duplicate Classification      (this file)
        ↓
    Cluster Assignment            (this file)
        ↓
    Structured DuplicateResult

Architecture mirrors llm.py:
    - Single public function as the entry point.
    - Comprehensive error handling with structured fallback.
    - Structured logging throughout the lifecycle.
    - All internal orchestration is private.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from .config import (
    CATEGORY_BOOST,
    CATEGORY_PENALTY,
    LOCATION_BOOST,
    POSSIBLE_DUPLICATE_THRESHOLD,
    SEARCH_LIMIT,
    SIMILARITY_THRESHOLD,
)
from .embedder import generate_embedding
from .exceptions import DuplicateDetectionError
from .models import ComplaintVector, DuplicateMatch, DuplicateResult
from .vector_store import (
    insert_complaint,
    search_similar,
)

# =============================================================================
# LOGGING
# =============================================================================

logger = logging.getLogger("civicflow.ai.duplicate.detector")

# =============================================================================
# CONSTANTS
# =============================================================================

_DUPLICATE_TYPE_DUPLICATE: str = "duplicate"
_DUPLICATE_TYPE_POSSIBLE: str = "possible_duplicate"
_DUPLICATE_TYPE_NEW: str = "new"


# =============================================================================
# PRIVATE — SIMILARITY ADJUSTMENT
# =============================================================================


def _normalise_text(text: str | None) -> str:
    """Lowercase and strip a string for fuzzy comparison.

    Args:
        text: Input text, possibly None.

    Returns:
        Normalised lowercase string, or empty string if None.
    """
    if text is None:
        return ""
    return text.strip().lower()


def _locations_match(location_a: str | None, location_b: str | None) -> bool:
    """Determine whether two location strings refer to the same place.

    Uses substring containment after normalisation as a lightweight
    heuristic. A full geocoding comparison can replace this later.

    Args:
        location_a: First location string.
        location_b: Second location string.

    Returns:
        True if the locations are considered matching.
    """
    norm_a = _normalise_text(location_a)
    norm_b = _normalise_text(location_b)

    if not norm_a or not norm_b:
        return False

    return norm_a in norm_b or norm_b in norm_a


def _adjust_similarity(
    raw_score: float,
    incoming_category: str | None,
    incoming_location: str | None,
    matched_category: str | None,
    matched_location: str | None,
) -> tuple[float, list[str]]:
    """Apply contextual boosts and penalties to a raw similarity score.

    Boosts:
        - Same location   → + LOCATION_BOOST
        - Same category   → + CATEGORY_BOOST

    Penalties:
        - Different category → score × CATEGORY_PENALTY

    The adjusted score is clamped to [0.0, 1.0].

    Args:
        raw_score:          Cosine similarity from the vector store.
        incoming_category:  Category of the new complaint.
        incoming_location:  Location of the new complaint.
        matched_category:   Category of the candidate match.
        matched_location:   Location of the candidate match.

    Returns:
        A tuple of (adjusted_score, list_of_reasons).
    """
    adjusted = raw_score
    reasons: list[str] = []

    if raw_score >= POSSIBLE_DUPLICATE_THRESHOLD:
        reasons.append("High semantic similarity")

    same_category = (
        _normalise_text(incoming_category) == _normalise_text(matched_category)
        and _normalise_text(incoming_category) != ""
    )

    same_location = _locations_match(incoming_location, matched_location)

    if same_category:
        adjusted += CATEGORY_BOOST
        reasons.append("Same category")
    elif (
        _normalise_text(incoming_category) != ""
        and _normalise_text(matched_category) != ""
    ):
        adjusted *= CATEGORY_PENALTY
        reasons.append("Different category (confidence reduced)")

    if same_location:
        adjusted += LOCATION_BOOST
        reasons.append("Nearby location")
    elif (
        _normalise_text(incoming_location) != ""
        and _normalise_text(matched_location) != ""
    ):
        reasons.append("Different location")

    adjusted = max(0.0, min(1.0, adjusted))

    return adjusted, reasons


# =============================================================================
# PRIVATE — CLASSIFICATION
# =============================================================================


def _classify_duplicate(score: float) -> tuple[bool, str]:
    """Classify a similarity score into a duplicate type.

    Thresholds are sourced from config.py.

    Args:
        score: Adjusted similarity score in [0.0, 1.0].

    Returns:
        Tuple of (is_duplicate, duplicate_type_string).
    """
    if score >= SIMILARITY_THRESHOLD:
        return True, _DUPLICATE_TYPE_DUPLICATE

    if score >= POSSIBLE_DUPLICATE_THRESHOLD:
        return True, _DUPLICATE_TYPE_POSSIBLE

    return False, _DUPLICATE_TYPE_NEW


# =============================================================================
# PRIVATE — CLUSTER MANAGEMENT
# =============================================================================


def _generate_cluster_id() -> str:
    """Generate a unique cluster identifier.

    Format: "cluster_<short-uuid>" to remain human-readable in logs
    and dashboards while guaranteeing uniqueness.

    Returns:
        A new cluster ID string.
    """
    short_id = uuid.uuid4().hex[:8]
    return f"cluster_{short_id}"


def _count_cluster_members(
    cluster_id: str,
    search_results: list[dict[str, Any]],
) -> int:
    """Count how many search results belong to a given cluster.

    This is a lightweight count derived from the current search batch.
    For exact counts at scale, query the vector store directly.

    Args:
        cluster_id:      The cluster to count.
        search_results:  Results from the vector store search.

    Returns:
        Number of matching results, minimum 1 (the new complaint itself).
    """
    count = sum(
        1
        for result in search_results
        if result.get("payload", {}).get("cluster_id") == cluster_id
    )
    return max(1, count)


# =============================================================================
# PRIVATE — BEST MATCH SELECTION
# =============================================================================


def _find_best_match(
    search_results: list[dict[str, Any]],
    incoming_category: str | None,
    incoming_location: str | None,
) -> DuplicateMatch | None:
    """Find the single best matching complaint from search results.

    Iterates through all candidates, adjusts scores, and selects
    the highest-scoring match.

    Args:
        search_results:    Raw results from vector store search.
        incoming_category: Category of the new complaint.
        incoming_location: Location of the new complaint.

    Returns:
        The best DuplicateMatch, or None if no results.
    """
    if not search_results:
        return None

    best_match: DuplicateMatch | None = None

    for result in search_results:
        payload = result.get("payload", {})
        raw_score = result.get("score", 0.0)

        adjusted_score, reasons = _adjust_similarity(
            raw_score=raw_score,
            incoming_category=incoming_category,
            incoming_location=incoming_location,
            matched_category=payload.get("category"),
            matched_location=payload.get("location"),
        )

        candidate = DuplicateMatch(
            complaint_id=payload.get("complaint_id", ""),
            cluster_id=payload.get("cluster_id", ""),
            raw_score=raw_score,
            adjusted_score=adjusted_score,
            category=payload.get("category"),
            location=payload.get("location"),
            reasons=reasons,
        )

        if best_match is None or candidate.adjusted_score > best_match.adjusted_score:
            best_match = candidate

    return best_match


# =============================================================================
# PRIVATE — STORE NEW COMPLAINT
# =============================================================================


def _store_complaint(
    complaint_id: str,
    cluster_id: str,
    vector: list[float],
    complaint_data: dict[str, Any],
) -> None:
    """Persist a complaint in the vector store.

    Args:
        complaint_id:   Unique ID for this complaint.
        cluster_id:     Cluster this complaint is assigned to.
        vector:         Embedding vector.
        complaint_data: Structured complaint from the LLM module.
    """
    complaint_vector = ComplaintVector(
        complaint_id=complaint_id,
        cluster_id=cluster_id,
        category=complaint_data.get("category"),
        location=complaint_data.get("location"),
        summary=complaint_data.get("summary"),
        department=complaint_data.get("department"),
        urgency=complaint_data.get("urgency"),
    )

    insert_complaint(
        complaint_id=complaint_id,
        vector=vector,
        payload=complaint_vector.to_payload(),
    )


# =============================================================================
# PRIVATE — FALLBACK RESULT
# =============================================================================


def _build_fallback_result(reason: str) -> DuplicateResult:
    """Build a safe fallback result when the pipeline cannot complete.

    The complaint is treated as new with a fresh cluster.

    Args:
        reason: Human-readable explanation of the fallback.

    Returns:
        A DuplicateResult indicating a new, unclustered complaint.
    """
    return DuplicateResult(
        is_duplicate=False,
        duplicate_type=_DUPLICATE_TYPE_NEW,
        cluster_id=_generate_cluster_id(),
        matched_complaint_id=None,
        cluster_size=1,
        similarity_score=0.0,
        reason=[reason],
    )


# =============================================================================
# PUBLIC API
# =============================================================================


def find_duplicate_complaint(
    complaint_data: dict[str, Any],
    complaint_id: str | None = None,
) -> dict[str, Any]:
    """Detect whether a complaint is a duplicate and assign it to a cluster.

    This is the ONLY public function that should be used by the rest
    of CivicFlow AI.

    Pipeline:
        Structured Complaint JSON
            ↓
        Summary Extraction
            ↓
        Embedding Generation
            ↓
        Vector Database Search
            ↓
        Similarity Calculation
            ↓
        Duplicate Classification
            ↓
        Cluster Assignment
            ↓
        Structured Result

    Args:
        complaint_data: Structured complaint dictionary from the LLM module.
            Expected keys: category, department, urgency, location,
            summary, confidence.
        complaint_id: Optional unique identifier for the complaint.
            If not provided, a UUID is generated.

    Returns:
        A dictionary matching the DuplicateResult schema:
            {
                "is_duplicate": bool,
                "duplicate_type": str,
                "cluster_id": str,
                "matched_complaint_id": str | None,
                "cluster_size": int,
                "similarity_score": float,
                "reason": list[str]
            }
    """
    start_time = time.perf_counter()

    logger.info("=" * 80)
    logger.info("Starting Duplicate Detection")

    if complaint_id is None:
        complaint_id = f"cmp_{uuid.uuid4().hex[:8]}"

    logger.info("Complaint ID    : %s", complaint_id)
    logger.info(
        "Category        : %s",
        complaint_data.get("category", "N/A"),
    )
    logger.info(
        "Location        : %s",
        complaint_data.get("location", "N/A"),
    )

    # ------------------------------------------------------------------
    # Validate Input
    # ------------------------------------------------------------------

    summary = complaint_data.get("summary")

    if not summary or not isinstance(summary, str) or not summary.strip():
        logger.warning("No summary provided. Treating as new complaint.")
        result = _build_fallback_result(
            "No summary available for similarity analysis."
        )
        logger.info("=" * 80)
        return result.model_dump()

    try:
        # --------------------------------------------------------------
        # Generate Embedding
        # --------------------------------------------------------------

        logger.info("Generating embedding for complaint summary.")

        vector = generate_embedding(summary)

        logger.debug(
            "Embedding generated: %d dimensions.",
            len(vector),
        )

        # --------------------------------------------------------------
        # Search Vector Store
        # --------------------------------------------------------------

        logger.info("Searching for similar complaints.")

        search_results = search_similar(
            vector=vector,
            limit=SEARCH_LIMIT,
        )

        logger.info(
            "Found %d candidate matches.",
            len(search_results),
        )

        # --------------------------------------------------------------
        # Find Best Match
        # --------------------------------------------------------------

        best_match = _find_best_match(
            search_results=search_results,
            incoming_category=complaint_data.get("category"),
            incoming_location=complaint_data.get("location"),
        )

        # --------------------------------------------------------------
        # Classify and Assign Cluster
        # --------------------------------------------------------------

        if best_match is not None and best_match.adjusted_score >= POSSIBLE_DUPLICATE_THRESHOLD:

            is_duplicate, duplicate_type = _classify_duplicate(
                best_match.adjusted_score,
            )

            cluster_id = best_match.cluster_id
            cluster_size = _count_cluster_members(
                cluster_id, search_results
            ) + 1

            logger.info(
                "Match found: %s (score=%.4f, type=%s, cluster=%s)",
                best_match.complaint_id,
                best_match.adjusted_score,
                duplicate_type,
                cluster_id,
            )

            result = DuplicateResult(
                is_duplicate=is_duplicate,
                duplicate_type=duplicate_type,
                cluster_id=cluster_id,
                matched_complaint_id=best_match.complaint_id,
                cluster_size=cluster_size,
                similarity_score=round(best_match.adjusted_score, 4),
                reason=best_match.reasons,
            )

        else:
            cluster_id = _generate_cluster_id()

            logger.info(
                "No duplicate found. Creating new cluster: %s",
                cluster_id,
            )

            reason_parts: list[str] = ["No similar complaints found"]

            if best_match is not None:
                reason_parts.append(
                    f"Best match score {best_match.adjusted_score:.4f} "
                    f"below threshold {POSSIBLE_DUPLICATE_THRESHOLD}"
                )

            result = DuplicateResult(
                is_duplicate=False,
                duplicate_type=_DUPLICATE_TYPE_NEW,
                cluster_id=cluster_id,
                matched_complaint_id=None,
                cluster_size=1,
                similarity_score=(
                    round(best_match.adjusted_score, 4)
                    if best_match is not None
                    else 0.0
                ),
                reason=reason_parts,
            )

        # --------------------------------------------------------------
        # Store Complaint in Vector Database
        # --------------------------------------------------------------

        _store_complaint(
            complaint_id=complaint_id,
            cluster_id=result.cluster_id,
            vector=vector,
            complaint_data=complaint_data,
        )

        logger.info(
            "Complaint stored in cluster '%s'.",
            result.cluster_id,
        )

        elapsed = time.perf_counter() - start_time

        logger.info(
            "Duplicate detection completed in %.2f seconds.",
            elapsed,
        )

        logger.info("=" * 80)

        return result.model_dump()

    # ------------------------------------------------------------------
    # Embedding Errors
    # ------------------------------------------------------------------

    except DuplicateDetectionError as exc:
        logger.error("=" * 80)
        logger.error("Duplicate Detection Error: %s", exc.message)
        logger.error("=" * 80)

        return _build_fallback_result(
            f"Detection failed: {exc.message}"
        ).model_dump()

    # ------------------------------------------------------------------
    # Unexpected Errors
    # ------------------------------------------------------------------

    except Exception as exc:
        logger.exception(
            "Unexpected error during duplicate detection."
        )

        return _build_fallback_result(
            f"Unexpected error: {exc}"
        ).model_dump()
