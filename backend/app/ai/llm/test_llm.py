"""
Simple test script for CivicFlow AI LLM module.

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


def print_result(title: str, result: dict):
    """Pretty-print a result."""
    print("=" * 80)
    print(title)
    print("=" * 80)
    print(json.dumps(result, indent=4, ensure_ascii=False))
    print()


def test_text_only():
    complaint = (
        "There is a huge pothole near Hanuman Mandir Chowk. "
        "Many bikes have slipped here during rain."
    )

    start = time.perf_counter()

    result = extract_complaint_information(
        complaint_text=complaint
    )

    elapsed = time.perf_counter() - start

    print_result("TEXT ONLY TEST", result)
    print(f"Time: {elapsed:.2f} sec\n")


def test_multilingual():
    complaint = (
        "हनुमान मंदिर के पास सड़क पर बड़ा गड्ढा है। "
        "बहुत दुर्घटनाएँ हो रही हैं।"
    )

    start = time.perf_counter()

    result = extract_complaint_information(
        complaint_text=complaint
    )

    elapsed = time.perf_counter() - start

    print_result("MULTILINGUAL TEST", result)
    print(f"Time: {elapsed:.2f} sec\n")


def test_code_mixed():
    complaint = (
        "ABC School ke samne road full damage hai. "
        "Cars ko bahut problem ho rahi hai."
    )

    start = time.perf_counter()

    result = extract_complaint_information(
        complaint_text=complaint
    )

    elapsed = time.perf_counter() - start

    print_result("CODE MIXED TEST", result)
    print(f"Time: {elapsed:.2f} sec\n")


def test_with_image():
    """
    Replace the image path with a real image if available.
    """

    image_path = "sample.jpg"

    if not Path(image_path).exists():
        print("=" * 80)
        print("IMAGE TEST")
        print("=" * 80)
        print("sample.jpg not found. Skipping image test.\n")
        return

    complaint = "There is a broken streetlight near City Hospital."

    result = extract_complaint_information(
        complaint_text=complaint,
        image_path=image_path,
    )

    print_result("IMAGE TEST", result)


def main():
    print("\n")
    print("#" * 80)
    print("CIVICFLOW AI - LLM MODULE TEST")
    print("#" * 80)
    print()

    test_text_only()

    test_multilingual()

    test_code_mixed()


    test_with_image()

    print("=" * 80)
    print("All tests completed.")
    print("=" * 80)


if __name__ == "__main__":
    main()