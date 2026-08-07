"""
Main AI Pipeline for CivicFlow AI.

Pipeline Flow

Complaint
    │
    ▼
Vision LLM Extraction
    │
    ▼
Duplicate Detection
    │
    ▼
Priority Engine
    │
    ▼
Routing Engine
    │
    ▼
Structured AI Response

This module exposes a single public function:

    process_complaint()
"""

from __future__ import annotations

import logging
import time
from typing import Any

from .duplicate import find_duplicate_complaint
from .llm import extract_complaint_information
from .priority import calculate_priority
from .routing import calculate_route

logger = logging.getLogger("civicflow.ai.pipeline")

PIPELINE_VERSION = "1.0.0"


def process_complaint(
    complaint_text: str,
    image_path: str | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    """
    Execute the complete CivicFlow AI pipeline.

    Pipeline Stages

    1. Vision LLM Extraction
    2. Duplicate Detection
    3. Priority Engine
    4. Routing Engine

    Parameters
    ----------
    complaint_text:
        Citizen complaint.

    image_path:
        Optional uploaded image.

    location:
        Optional location.

    Returns
    -------
    dict
        Fully structured pipeline response.
    """

    pipeline_start = time.perf_counter()

    logger.info("=" * 80)
    logger.info("Starting CivicFlow AI Pipeline")

    try:

        #######################################################################
        # Stage 1
        # Vision LLM Extraction
        #######################################################################

        logger.info("Stage 1/4 : Vision LLM Extraction")

        stage_start = time.perf_counter()

        llm_result = extract_complaint_information(
            complaint_text=complaint_text,
            image_path=image_path,
            location=location,
        )

        logger.info(
            "Vision LLM completed in %.2f sec",
            time.perf_counter() - stage_start,
        )

        #######################################################################
        # Stage 2
        # Duplicate Detection
        #######################################################################

        logger.info("Stage 2/4 : Duplicate Detection")

        stage_start = time.perf_counter()

        duplicate_result = find_duplicate_complaint(
            complaint_data=llm_result,
        )

        logger.info(
            "Duplicate Detection completed in %.2f sec",
            time.perf_counter() - stage_start,
        )

        #######################################################################
        # Stage 3
        # Priority Engine
        #######################################################################

        logger.info("Stage 3/4 : Priority Engine")

        stage_start = time.perf_counter()

        priority_result = calculate_priority(
            complaint_data=llm_result,
            duplicate_data=duplicate_result,
        )

        logger.info(
            "Priority Engine completed in %.2f sec",
            time.perf_counter() - stage_start,
        )
                #######################################################################
        # Stage 4
        # Routing Engine
        #######################################################################

        logger.info("Stage 4/4 : Routing Engine")

        stage_start = time.perf_counter()

        routing_result = calculate_route(
            complaint_data=llm_result,
            duplicate_data=duplicate_result,
            priority_data=priority_result,
        )

        logger.info(
            "Routing Engine completed in %.2f sec",
            time.perf_counter() - stage_start,
        )

        #######################################################################
        # Pipeline Summary
        #######################################################################

        pipeline_summary = {
            "category": llm_result.get("category"),
            "urgency": llm_result.get("urgency"),
            "is_duplicate": duplicate_result.get("is_duplicate"),
            "priority": priority_result.get("priority_level"),
            "priority_score": priority_result.get("priority_score"),
            "department": routing_result.get("department"),
            "team": routing_result.get("team"),
            "zone": routing_result.get("zone"),
            "sla_hours": routing_result.get("sla_hours"),
            "requires_escalation": routing_result.get(
                "requires_escalation"
            ),
        }

        #######################################################################
        # Final Response
        #######################################################################

        final_result = {
            "status": "success",
            "pipeline_version": PIPELINE_VERSION,
            "execution_time_seconds": round(
                time.perf_counter() - pipeline_start,
                3,
            ),
            "input": {
                "complaint_text": complaint_text,
                "image_path": image_path,
                "location": location,
            },
            "complaint": llm_result,
            "analysis": {
                "duplicate": duplicate_result,
                "priority": priority_result,
                "routing": routing_result,
            },
            "summary": pipeline_summary,
        }

        logger.info(
            "Pipeline completed successfully in %.2f sec",
            final_result["execution_time_seconds"],
        )

        logger.info("=" * 80)

        return final_result

    ###########################################################################
    # Error Handling
    ###########################################################################

    except Exception as exc:

        logger.exception(
            "Pipeline execution failed.",
            exc_info=exc,
        )

        return {
            "status": "failed",
            "pipeline_version": PIPELINE_VERSION,
            "execution_time_seconds": round(
                time.perf_counter() - pipeline_start,
                3,
            ),
            "error": {
                "type": exc.__class__.__name__,
                "message": str(exc),
            },
        }