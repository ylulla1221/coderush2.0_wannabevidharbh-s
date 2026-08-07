"""
LLM integration module for CivicFlow AI.

This module provides the SOLE interface for all LLM interactions across
the entire CivicFlow AI system. No other module should call the LLM
directly — everything routes through `extract_complaint_information()`.

Architecture:
    prompts.py  →  defines all prompt templates & formatting helpers
    llm.py      →  owns the LLM client, request lifecycle, and response parsing

Swapping the LLM:
    1. Change LLM_BASE_URL and LLM_MODEL in environment variables.
    2. If the new model's API is not OpenAI-compatible, only `_call_llm()`
       and `_call_llm_with_vision()` need modification.
    3. Prompts can be adjusted in prompts.py without touching this file.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import httpx

from .prompts import (
    FALLBACK_RESPONSE,
    SYSTEM_PROMPT,
    VISION_ADDENDUM,
    build_user_prompt,
)

# =============================================================================
# LOGGING
# =============================================================================

logger = logging.getLogger("civicflow.ai.llm")

# =============================================================================
# CONFIGURATION (all from environment — zero hardcoded secrets)
# =============================================================================

LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_MODEL: str = os.getenv("LLM_MODEL", "bharatcode:qwen36-35b-q6-256k-vision")
LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "120"))
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "1024"))

# =============================================================================
# TYPE ALIASES
# =============================================================================

ComplaintResult = dict[str, Any]


# =============================================================================
# PRIVATE HELPERS
# =============================================================================


def _encode_image_to_base64(image_path: str) -> str:
    """
    Read an image file and return its base64-encoded string.

    Args:
        image_path: Absolute or relative path to the image file.

    Returns:
        Base64-encoded image string.

    Raises:
        FileNotFoundError: If the image file does not exist.
        PermissionError: If the file cannot be read.
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _detect_mime_type(image_path: str) -> str:
    """
    Detect MIME type from file extension.

    Args:
        image_path: Path to the image file.

    Returns:
        MIME type string (e.g., 'image/jpeg').
    """
    suffix = Path(image_path).suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
    }
    return mime_map.get(suffix, "image/jpeg")


def _build_messages(
    user_prompt: str,
    image_path: str | None = None,
) -> list[dict[str, Any]]:
    """
    Build the messages array for the OpenAI-compatible chat API.

    When an image is provided, the user message is constructed as a
    multimodal content block (text + image_url) and the vision addendum
    is appended to the text portion.

    Args:
        user_prompt: The assembled user prompt text.
        image_path: Optional path to the complaint image.

    Returns:
        List of message dictionaries ready for the API.
    """
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]

    if image_path:
        # Multimodal message with text + image
        base64_img = _encode_image_to_base64(image_path)
        mime_type = _detect_mime_type(image_path)

        prompt_with_vision = f"{user_prompt}\n\n{VISION_ADDENDUM}"

        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt_with_vision},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{base64_img}",
                    },
                },
            ],
        })
    else:
        # Text-only message
        messages.append({"role": "user", "content": user_prompt})

    return messages


def _call_llm(messages: list[dict[str, Any]]) -> str:
    """
    Send a chat completion request to the LLM and return the raw
    response content.

    Uses httpx for synchronous HTTP (compatible with FastAPI's
    run_in_executor pattern for CPU-bound AI pipelines). If you
    later need fully async calls, swap to httpx.AsyncClient.

    Args:
        messages: The messages array for the chat API.

    Returns:
        Raw string content from the model's response.

    Raises:
        httpx.HTTPStatusError: On non-2xx responses from the LLM API.
        httpx.TimeoutException: If the request exceeds LLM_TIMEOUT.
    """
    url = f"{LLM_BASE_URL}/chat/completions"

    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": LLM_TEMPERATURE,
        "max_tokens": LLM_MAX_TOKENS,
        "stream": False,
    }

    logger.debug("Sending request to LLM at %s with model %s", url, LLM_MODEL)

    with httpx.Client(timeout=LLM_TIMEOUT) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()

    data = response.json()
    content: str = data["choices"][0]["message"]["content"]

    logger.debug("LLM raw response length: %d characters", len(content))

    return content


def _parse_llm_response(raw_response: str) -> ComplaintResult:
    """
    Parse and validate the LLM's JSON response.

    Handles common LLM quirks:
    - Strips markdown code fences (```json ... ```)
    - Strips leading/trailing whitespace
    - Validates all required keys are present

    Args:
        raw_response: The raw string returned by the LLM.

    Returns:
        Validated dictionary with all required fields.

    Raises:
        ValueError: If the response cannot be parsed as valid JSON.
    """
    cleaned = raw_response.strip()

    # Strip markdown code fences if the model wraps output
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Remove first line (```json) and last line (```)
        lines = [
            line for line in lines
            if not line.strip().startswith("```")
        ]
        cleaned = "\n".join(lines).strip()

    try:
        parsed: dict[str, Any] = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse LLM response as JSON: %s", e)
        logger.error("Raw response was: %s", raw_response[:500])
        raise ValueError(f"LLM returned invalid JSON: {e}") from e

    # Validate required keys
    required_keys = {"category", "department", "urgency", "location", "summary", "confidence"}
    missing = required_keys - set(parsed.keys())
    if missing:
        logger.warning("LLM response missing keys: %s. Filling with null.", missing)
        for key in missing:
            parsed[key] = None

    # Clamp confidence to [0.0, 1.0]
    if parsed.get("confidence") is not None:
        try:
            parsed["confidence"] = max(0.0, min(1.0, float(parsed["confidence"])))
        except (TypeError, ValueError):
            logger.warning("Invalid confidence value: %s. Setting to 0.0.", parsed["confidence"])
            parsed["confidence"] = 0.0

    # Validate urgency enum
    valid_urgencies = {"Critical", "High", "Medium", "Low", None}
    if parsed.get("urgency") not in valid_urgencies:
        logger.warning(
            "Invalid urgency '%s'. Attempting case-insensitive match.",
            parsed.get("urgency"),
        )
        # Attempt case-insensitive correction
        if parsed.get("urgency") and isinstance(parsed["urgency"], str):
            for valid in {"Critical", "High", "Medium", "Low"}:
                if parsed["urgency"].lower() == valid.lower():
                    parsed["urgency"] = valid
                    break
            else:
                parsed["urgency"] = None

    return parsed


# =============================================================================
# PUBLIC API — THE SINGLE ENTRY POINT
# =============================================================================


def extract_complaint_information(
    complaint_text: str,
    yolo_detection: dict[str, Any] | None = None,
    image_path: str | None = None,
) -> ComplaintResult:
    """
    Extract structured civic complaint information using the LLM.

    This is the ONLY function external modules should call.
    It fuses complaint text, optional YOLO detections, and optional
    image analysis into a single structured JSON result.

    Pipeline position:
        YOLO Detection → **extract_complaint_information()** → Embedding Generation

    Args:
        complaint_text: The resident's complaint in any supported
            language (English, Hindi, Marathi, or code-mixed).
        yolo_detection: Optional dictionary of YOLO detection results.
            Expected format:
            {
                "detections": [
                    {"class": "Pothole", "confidence": 0.92},
                    {"class": "Road Crack", "confidence": 0.85}
                ]
            }
        image_path: Optional path to the complaint image for
            vision model analysis.

    Returns:
        Dictionary with keys:
            - category (str | None)
            - department (str | None)
            - urgency (str | None): "Critical" | "High" | "Medium" | "Low"
            - location (str | None)
            - summary (str | None)
            - confidence (float): 0.0 to 1.0

    Example:
        >>> result = extract_complaint_information(
        ...     complaint_text="ABC School ke paas bahut bada pothole hai",
        ...     yolo_detection={
        ...         "detections": [{"class": "Pothole", "confidence": 0.92}]
        ...     },
        ...     image_path="/uploads/complaint_42.jpg",
        ... )
        >>> result
        {
            "category": "Road Damage",
            "department": "Road Department",
            "urgency": "High",
            "location": "Near ABC School",
            "summary": "Large pothole reported near ABC School causing traffic issues.",
            "confidence": 0.95
        }
    """
    start_time = time.time()

    logger.info(
        "Processing complaint — text length: %d, YOLO: %s, image: %s",
        len(complaint_text),
        "yes" if yolo_detection else "no",
        "yes" if image_path else "no",
    )

    # ── Guard: empty complaint text ──────────────────────────────────────
    if not complaint_text or not complaint_text.strip():
        logger.warning("Empty complaint text received. Returning fallback.")
        return {**FALLBACK_RESPONSE}

    # ── Validate image path if provided ──────────────────────────────────
    if image_path and not Path(image_path).exists():
        logger.warning(
            "Image path '%s' does not exist. Proceeding without image.",
            image_path,
        )
        image_path = None

    try:
        # ── Step 1: Build the user prompt ────────────────────────────────
        user_prompt = build_user_prompt(
            complaint_text=complaint_text,
            yolo_detection=yolo_detection,
        )

        # ── Step 2: Build the messages array ─────────────────────────────
        messages = _build_messages(
            user_prompt=user_prompt,
            image_path=image_path,
        )

        # ── Step 3: Call the LLM ─────────────────────────────────────────
        raw_response = _call_llm(messages)

        # ── Step 4: Parse and validate the response ──────────────────────
        result = _parse_llm_response(raw_response)

        elapsed = time.time() - start_time
        logger.info(
            "Complaint processed in %.2fs — category: %s, urgency: %s, confidence: %.2f",
            elapsed,
            result.get("category"),
            result.get("urgency"),
            result.get("confidence", 0.0),
        )

        return result

    except (httpx.HTTPStatusError, httpx.TimeoutException) as e:
        logger.error("LLM API error: %s", e)
        return {**FALLBACK_RESPONSE}

    except ValueError as e:
        logger.error("Response parsing error: %s", e)
        return {**FALLBACK_RESPONSE}

    except Exception as e:
        logger.error("Unexpected error during complaint extraction: %s", e, exc_info=True)
        return {**FALLBACK_RESPONSE}
