"""
LLM integration module for CivicFlow AI.

This module provides the SOLE interface for all LLM interactions across
the entire CivicFlow AI system. No other module should call the LLM
directly — everything routes through `extract_complaint_information()`.

Architecture:
    prompts.py  →  Prompt templates
    llm.py      →  LLM client + request lifecycle + response parsing

Supports:
- BharatCode Chat API
- BharatCode Vision API
- OpenAI-compatible message format
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
from dotenv import load_dotenv

from .prompts import (
    FALLBACK_RESPONSE,
    SYSTEM_PROMPT,
    VISION_ADDENDUM,
    build_user_prompt,
)

# =============================================================================
# LOAD ENVIRONMENT
# =============================================================================

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

# =============================================================================
# LOGGING
# =============================================================================

logger = logging.getLogger("civicflow.ai.llm")

# =============================================================================
# CONFIGURATION
# =============================================================================

LLM_BASE_URL: str = os.getenv(
    "LLM_BASE_URL",
    "https://bharatcode.ai/api/model/v1",
)

LLM_MODEL: str = os.getenv(
    "LLM_MODEL",
    "bharatcode:qwen36-35b-q6-256k-vision",
)

BHARATCODE_API_KEY: str | None = os.getenv("BHARATCODE_API_KEY")

LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "120"))
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "1024"))

if not BHARATCODE_API_KEY:
    raise RuntimeError(
        "BHARATCODE_API_KEY not found. Please configure backend/.env"
    )

ComplaintResult = dict[str, Any]

# =============================================================================
# PRIVATE HELPERS
# =============================================================================


def _build_headers() -> dict[str, str]:
    """
    Build authentication headers for BharatCode API.
    """

    return {
        "Authorization": f"Bearer {BHARATCODE_API_KEY}",
        "Content-Type": "application/json",
    }


def _encode_image_to_base64(image_path: str) -> str:
    """
    Encode an image to Base64 for BharatCode Vision.
    """

    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _detect_mime_type(image_path: str) -> str:
    """
    Detect image MIME type from extension.
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
    # =============================================================================
# MESSAGE BUILDING
# =============================================================================

def _build_messages(
    user_prompt: str,
    image_path: str | None = None,
) -> list[dict[str, Any]]:
    """
    Build the OpenAI-compatible messages array for BharatCode.

    If an image is supplied, create a multimodal message consisting
    of text + image_url (base64 encoded).
    """

    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    ]

    # ---------------------------------------------------------
    # Text only
    # ---------------------------------------------------------

    if image_path is None:
        messages.append(
            {
                "role": "user",
                "content": user_prompt,
            }
        )

        return messages

    # ---------------------------------------------------------
    # Vision request
    # ---------------------------------------------------------

    base64_image = _encode_image_to_base64(image_path)
    mime_type = _detect_mime_type(image_path)

    prompt = f"{user_prompt}\n\n{VISION_ADDENDUM}"

    messages.append(
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt,
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": (
                            f"data:{mime_type};base64,{base64_image}"
                        )
                    },
                },
            ],
        }
    )

    return messages


# =============================================================================
# LLM CALL
# =============================================================================

def _call_llm(messages: list[dict[str, Any]]) -> str:
    """
    Send a request to BharatCode Chat API.

    Parameters
    ----------
    messages:
        OpenAI-compatible messages list.

    Returns
    -------
    str
        Raw assistant response.

    Raises
    ------
    httpx.HTTPStatusError
        If BharatCode returns a non-200 response.

    httpx.TimeoutException
        If the request exceeds the configured timeout.

    ValueError
        If BharatCode returns an unexpected response.
    """

    url = f"{LLM_BASE_URL}/chat/completions"

    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": LLM_TEMPERATURE,
        "max_tokens": LLM_MAX_TOKENS,
        "stream": False,
    }

    headers = _build_headers()

    logger.info("Calling BharatCode model: %s", LLM_MODEL)

    logger.debug("POST %s", url)

    with httpx.Client(timeout=LLM_TIMEOUT) as client:

        response = client.post(
            url=url,
            headers=headers,
            json=payload,
        )

        logger.debug(
            "HTTP %s returned %d",
            url,
            response.status_code,
        )

        response.raise_for_status()

    data = response.json()
   

    if "choices" not in data:
        logger.error("Unexpected BharatCode response: %s", data)
        raise ValueError(
            "Response does not contain 'choices'."
        )

    if not data["choices"]:
        raise ValueError("No choices returned by BharatCode.")

    message = data["choices"][0].get("message")

    if message is None:
        raise ValueError("Missing 'message' in BharatCode response.")

    content = message.get("content")

    if content is None:
        raise ValueError("Missing 'content' in BharatCode response.")

    logger.debug(
        "Received %d characters from BharatCode.",
        len(content),
    )

    return content
# =============================================================================
# RESPONSE PARSER
# =============================================================================

def _parse_llm_response(raw_response: str) -> ComplaintResult:
    """
    Parse and validate BharatCode's JSON response.

    Handles common LLM issues:
    - Markdown code fences
    - Extra whitespace
    - Missing keys
    - Invalid confidence values
    - Invalid urgency values

    Returns
    -------
    ComplaintResult
    """

    cleaned = raw_response.strip()

    # ---------------------------------------------------------
    # Remove Markdown code fences if present
    # ---------------------------------------------------------

    if cleaned.startswith("```"):

        lines = cleaned.splitlines()

        lines = [
            line
            for line in lines
            if not line.strip().startswith("```")
        ]

        cleaned = "\n".join(lines).strip()

    # ---------------------------------------------------------
    # Parse JSON
    # ---------------------------------------------------------

    try:

        parsed: dict[str, Any] = json.loads(cleaned)

    except json.JSONDecodeError as e:

        logger.error("Failed to parse BharatCode JSON response.")
        logger.error("Raw response:\n%s", raw_response)

        raise ValueError(
            f"Invalid JSON returned by BharatCode: {e}"
        ) from e

    # ---------------------------------------------------------
    # Required Keys
    # ---------------------------------------------------------

    required_keys = {
        "category",
        "urgency",
        "location",
        "summary",
        "confidence",
    }

    missing_keys = required_keys - parsed.keys()

    if missing_keys:

        logger.warning(
            "Missing keys returned by LLM: %s",
            missing_keys,
        )

        for key in missing_keys:
            parsed[key] = None

    # ---------------------------------------------------------
    # Confidence Validation
    # ---------------------------------------------------------

    confidence = parsed.get("confidence")

    try:

        confidence = float(confidence)

        confidence = max(
            0.0,
            min(
                1.0,
                confidence,
            ),
        )

    except Exception:

        logger.warning(
            "Invalid confidence value '%s'. Defaulting to 0.0",
            confidence,
        )

        confidence = 0.0

    parsed["confidence"] = confidence

    # ---------------------------------------------------------
    # Urgency Validation
    # ---------------------------------------------------------

    valid_urgencies = {
        "Critical",
        "High",
        "Medium",
        "Low",
        None,
    }

    urgency = parsed.get("urgency")

    if urgency not in valid_urgencies:

        if isinstance(urgency, str):

            matched = False

            for valid in (
                "Critical",
                "High",
                "Medium",
                "Low",
            ):

                if urgency.lower() == valid.lower():

                    parsed["urgency"] = valid
                    matched = True
                    break

            if not matched:

                logger.warning(
                    "Unknown urgency '%s'. Setting to null.",
                    urgency,
                )

                parsed["urgency"] = None

        else:

            parsed["urgency"] = None

    # ---------------------------------------------------------
    # Normalize Strings
    # ---------------------------------------------------------

    for key in (
        "category",
        "location",
        "summary",
    ):

        value = parsed.get(key)

        if isinstance(value, str):

            parsed[key] = value.strip()

    logger.info(
        "LLM Extraction Successful | Category=%s | Urgency=%s | Confidence=%.2f",
        parsed.get("category"),
        parsed.get("urgency"),
        parsed.get("confidence"),
    )

    return parsed
# =============================================================================
# PUBLIC API
# =============================================================================

def extract_complaint_information(
    complaint_text: str,
    image_path: str | None = None,
    location: str | None = None,
) -> ComplaintResult:
    """
    Extract structured information from a civic complaint.

    This is the ONLY public function that should be used by the rest
    of CivicFlow AI.

    Pipeline

    Complaint
        ↓
    Prompt Construction
        ↓
    BharatCode Chat/Vision
        ↓
    JSON Parsing
        ↓
    Validation
        ↓
    Structured Complaint JSON

    Parameters
    ----------
    complaint_text
        Complaint text in English, Hindi, Marathi or code-mixed.

    image_path
        Optional complaint image.

    location
        Optional location reference.

    Returns
    -------
    ComplaintResult
    """

    start_time = time.perf_counter()

    logger.info("=" * 80)
    logger.info("Starting Complaint Extraction")

    logger.info(
        "Complaint Length : %d",
        len(complaint_text),
    )

    logger.info(
        "Location         : %s",
        "Yes" if location else "No",
    )

    logger.info(
        "Image Attached   : %s",
        "Yes" if image_path else "No",
    )

    # ------------------------------------------------------------------
    # Validate Complaint
    # ------------------------------------------------------------------

    if not complaint_text or not complaint_text.strip():

        logger.warning("Received empty complaint.")

        return {**FALLBACK_RESPONSE}

    # ------------------------------------------------------------------
    # Validate Image
    # ------------------------------------------------------------------

    if image_path:

        path = Path(image_path)

        if not path.exists():

            logger.warning(
                "Image '%s' does not exist. Ignoring image.",
                image_path,
            )

            image_path = None

    try:

        # --------------------------------------------------------------
        # Build Prompt
        # --------------------------------------------------------------

        user_prompt = build_user_prompt(
            complaint_text=complaint_text,
            location=location,
        )

        logger.debug("Prompt successfully generated.")

        # --------------------------------------------------------------
        # Build Messages
        # --------------------------------------------------------------

        messages = _build_messages(
            user_prompt=user_prompt,
            image_path=image_path,
        )

        # --------------------------------------------------------------
        # Call BharatCode
        # --------------------------------------------------------------

        raw_response = _call_llm(messages)

        logger.debug("Raw LLM response:\n%s", raw_response)

        # --------------------------------------------------------------
        # Parse Response
        # --------------------------------------------------------------

        result = _parse_llm_response(raw_response)

        elapsed = time.perf_counter() - start_time

        logger.info(
            "Complaint processed successfully in %.2f seconds.",
            elapsed,
        )

        logger.info("=" * 80)

        return result

    # ------------------------------------------------------------------
    # BharatCode HTTP Errors
    # ------------------------------------------------------------------

    except httpx.HTTPStatusError as e:

        logger.error("=" * 80)
        logger.error("BharatCode HTTP Error")

        if e.response is not None:

            logger.error(
                "Status Code : %s",
                e.response.status_code,
            )

            logger.error(
                "Response Body:\n%s",
                e.response.text,
            )

        logger.error("=" * 80)

        return {**FALLBACK_RESPONSE}

    # ------------------------------------------------------------------
    # Timeout
    # ------------------------------------------------------------------

    except httpx.TimeoutException as e:

        logger.error("=" * 80)
        logger.error("BharatCode Timeout")
        logger.error(str(e))
        logger.error("=" * 80)

        return {**FALLBACK_RESPONSE}

    # ------------------------------------------------------------------
    # Parsing Errors
    # ------------------------------------------------------------------

    except ValueError as e:

        logger.error("=" * 80)
        logger.error("Response Parsing Error")
        logger.error(str(e))
        logger.error("=" * 80)

        return {**FALLBACK_RESPONSE}

    # ------------------------------------------------------------------
    # Unexpected Errors
    # ------------------------------------------------------------------

    except Exception as e:

        logger.exception(
            "Unexpected error during complaint extraction."
        )

        logger.exception(e)

        return {**FALLBACK_RESPONSE}