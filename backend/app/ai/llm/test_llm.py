"""
Test script for the CivicFlow AI LLM module.

Verifies that extract_complaint_information() returns ONLY the five
fields the Vision LLM is responsible for:

    category, urgency, location, summary, confidence

The 'department' field must NOT appear in the result — routing
decisions are the exclusive responsibility of the Routing Engine.

Run:

    python -m app.ai.llm.test_llm

or

    python app/ai/llm/test_llm.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from .llm import extract_complaint_information

# =============================================================================
# EXPECTED OUTPUT SHAPE
# =============================================================================

# These are the ONLY keys the LLM module is allowed to produce.
# The Routing Engine owns department, team, zone, sla_hours, etc.
EXPECTED_KEYS: frozenset[str] = frozenset(
    {"category", "urgency", "location", "summary", "confidence"}
)

VALID_URGENCY_VALUES: frozenset[str | None] = frozenset(
    {"Critical", "High", "Medium", "Low", None}
)

# =============================================================================
# HELPERS
# =============================================================================


def print_result(title: str, result: dict) -> None:
    """Pretty-print a result dict."""
    print("=" * 80)
    print(title)
    print("=" * 80)
    print(json.dumps(result, indent=4, ensure_ascii=False))
    print()


def _assert_schema(result: dict, test_name: str) -> None:
    """Assert that result contains exactly the expected keys.

    Args:
        result: Dictionary returned by extract_complaint_information().
        test_name: Human-readable label used in assertion messages.

    Raises:
        AssertionError: If any unexpected key is present or an expected
            key is missing.
    """
    present = set(result.keys())

    # No unexpected keys
    unexpected = present - EXPECTED_KEYS
    assert not unexpected, (
        f"[{test_name}] Unexpected keys in LLM result: {unexpected}. "
        "Department/routing decisions must come from the Routing Engine only."
    )

    # All expected keys present
    missing = EXPECTED_KEYS - present
    assert not missing, (
        f"[{test_name}] Missing expected keys in LLM result: {missing}."
    )

    # department must be absent
    assert "department" not in result, (
        f"[{test_name}] 'department' MUST NOT be returned by the LLM module. "
        "Department assignment is the Routing Engine's responsibility."
    )

    # confidence is a float in [0.0, 1.0]
    confidence = result.get("confidence")
    assert isinstance(confidence, float), (
        f"[{test_name}] 'confidence' must be a float, got {type(confidence)}."
    )
    assert 0.0 <= confidence <= 1.0, (
        f"[{test_name}] 'confidence' must be in [0.0, 1.0], got {confidence}."
    )

    # urgency is one of the known values or null
    urgency = result.get("urgency")
    assert urgency in VALID_URGENCY_VALUES, (
        f"[{test_name}] 'urgency' must be Critical/High/Medium/Low/null, "
        f"got '{urgency}'."
    )

    print(f"  ✓ Schema correct — keys: {sorted(present)}")
    print(f"  ✓ urgency={urgency!r}  confidence={confidence:.2f}")


# =============================================================================
# TEST CASES
# =============================================================================


def test_text_only() -> None:
    """English complaint, no image, no location."""
    complaint = (
        "There is a huge pothole near Hanuman Mandir Chowk. "
        "Many bikes have slipped here during rain."
    )

    start = time.perf_counter()
    result = extract_complaint_information(complaint_text=complaint)
    elapsed = time.perf_counter() - start

    print_result("TEXT ONLY TEST", result)
    print(f"  Time: {elapsed:.2f} sec\n")
    _assert_schema(result, "test_text_only")


def test_multilingual() -> None:
    """Hindi complaint — verifies multi-language extraction."""
    complaint = (
        "हनुमान मंदिर के पास सड़क पर बड़ा गड्ढा है। "
        "बहुत दुर्घटनाएँ हो रही हैं।"
    )

    start = time.perf_counter()
    result = extract_complaint_information(complaint_text=complaint)
    elapsed = time.perf_counter() - start

    print_result("MULTILINGUAL TEST", result)
    print(f"  Time: {elapsed:.2f} sec\n")
    _assert_schema(result, "test_multilingual")


def test_code_mixed() -> None:
    """Hinglish / code-mixed complaint."""
    complaint = (
        "ABC School ke samne road full damage hai. "
        "Cars ko bahut problem ho rahi hai."
    )

    start = time.perf_counter()
    result = extract_complaint_information(complaint_text=complaint)
    elapsed = time.perf_counter() - start

    print_result("CODE MIXED TEST", result)
    print(f"  Time: {elapsed:.2f} sec\n")
    _assert_schema(result, "test_code_mixed")


def test_with_location() -> None:
    """Complaint with an explicit location reference passed as a parameter."""
    complaint = "The street light has been broken for two weeks."
    location = "MG Road, Near Central Bus Stand, Nagpur"

    start = time.perf_counter()
    result = extract_complaint_information(
        complaint_text=complaint,
        location=location,
    )
    elapsed = time.perf_counter() - start

    print_result("WITH LOCATION TEST", result)
    print(f"  Time: {elapsed:.2f} sec\n")
    _assert_schema(result, "test_with_location")

    # Location hint should surface in the result
    assert result.get("location") is not None, (
        "test_with_location: 'location' should not be null when an explicit "
        "location reference is provided."
    )
    print("  ✓ location is non-null as expected")


def test_empty_complaint() -> None:
    """An empty string must return the fallback — not raise."""
    result = extract_complaint_information(complaint_text="")

    print_result("EMPTY COMPLAINT TEST (fallback expected)", result)
    _assert_schema(result, "test_empty_complaint")

    # Fallback sets confidence to 0.0
    assert result["confidence"] == 0.0, (
        "test_empty_complaint: fallback must set confidence to 0.0."
    )
    print("  ✓ fallback returned correctly for empty complaint")


def test_with_image() -> None:
    """Vision test — skipped gracefully when sample.jpg is absent."""
    image_path = "sample.jpg"

    if not Path(image_path).exists():
        print("=" * 80)
        print("IMAGE TEST")
        print("=" * 80)
        print("  sample.jpg not found — skipping image test.\n")
        return

    complaint = "There is a broken streetlight near City Hospital."

    start = time.perf_counter()
    result = extract_complaint_information(
        complaint_text=complaint,
        image_path=image_path,
    )
    elapsed = time.perf_counter() - start

    print_result("IMAGE TEST", result)
    print(f"  Time: {elapsed:.2f} sec\n")
    _assert_schema(result, "test_with_image")


# =============================================================================
# MAIN
# =============================================================================


def main() -> None:
    print("\n")
    print("#" * 80)
    print("CIVICFLOW AI — LLM MODULE TEST")
    print("Verifying: category | urgency | location | summary | confidence")
    print("Must NOT contain: department | team | zone | sla_hours")
    print("#" * 80)
    print()

    test_text_only()
    test_multilingual()
    test_code_mixed()
    test_with_location()
    test_empty_complaint()
    test_with_image()

    print("=" * 80)
    print("All tests completed successfully.")
    print("=" * 80)


if __name__ == "__main__":
    main()