"""
Main AI Pipeline for CivicFlow AI.

This module orchestrates the complete flow:
Complaint -> Vision LLM Extraction -> Duplicate Detection
-> Priority Scoring -> Department Routing -> Explanation Generation -> Return JSON

Provides a single public entry point `process_complaint()`.
"""

import logging
from typing import Any, Dict

from .duplicate import find_duplicate_complaint
from .llm import extract_complaint_information
from .priority import calculate_priority

logger = logging.getLogger("civicflow.ai.pipeline")


def _stub_department_routing(complaint_data: Dict[str, Any]) -> Dict[str, Any]:
    """Stub for Department Routing."""
    department = complaint_data.get("department") or "General Administration"
    return {"assigned_department": department, "routing_confidence": 0.95}


def _stub_explanation_generation(complaint_data: Dict[str, Any], duplicate_data: Dict[str, Any]) -> str:
    """Stub for AI Explanation Generation."""
    category = complaint_data.get("category", "Unknown")
    is_dup = duplicate_data.get("is_duplicate", False)
    dup_str = " (Identified as a duplicate issue)" if is_dup else ""
    return f"This complaint was categorized as {category}{dup_str} and prioritized based on urgency."


def process_complaint(
    complaint_text: str,
    image_path: str | None = None,
    location: str | None = None,
) -> Dict[str, Any]:
    """
    Process a civic complaint through the full AI pipeline.
    
    Args:
        complaint_text: The resident's complaint text.
        image_path: Optional path to an uploaded image.
        location: Optional location string.
        
    Returns:
        A structured JSON-serializable dictionary with the final results.
    """
    logger.info("=" * 80)
    logger.info("Starting Full AI Pipeline for new complaint.")
    
    # ---------------------------------------------------------
    # Stage 1: Vision LLM Extraction
    # ---------------------------------------------------------
    logger.info("Stage 1: Vision LLM Extraction")
    llm_result = extract_complaint_information(
        complaint_text=complaint_text,
        image_path=image_path,
        location=location,
    )
    
    # ---------------------------------------------------------
    # Stage 2: Duplicate Detection (includes Embedding Generation)
    # ---------------------------------------------------------
    logger.info("Stage 2: Duplicate Detection")
    duplicate_result = find_duplicate_complaint(complaint_data=llm_result)
    
    # ---------------------------------------------------------
    # Stage 3: Priority Scoring
    # ---------------------------------------------------------
    logger.info("Stage 3: Priority Scoring")
    priority_result = calculate_priority(
        complaint_data=llm_result,
        duplicate_data=duplicate_result,
    )
    
    # ---------------------------------------------------------
    # Stage 4: Department Routing
    # ---------------------------------------------------------
    logger.info("Stage 4: Department Routing")
    routing_result = _stub_department_routing(llm_result)
    
    # ---------------------------------------------------------
    # Stage 5: AI Explanation Generation
    # ---------------------------------------------------------
    logger.info("Stage 5: Explanation Generation")
    explanation = _stub_explanation_generation(llm_result, duplicate_result)
    
    # ---------------------------------------------------------
    # Final Assembly
    # ---------------------------------------------------------
    final_result = {
        "extraction": llm_result,
        "duplicate_analysis": duplicate_result,
        "priority_analysis": priority_result,
        "routing_analysis": routing_result,
        "explanation": explanation,
        "status": "success",
    }
    
    logger.info("AI Pipeline completed successfully.")
    logger.info("=" * 80)
    
    return final_result
