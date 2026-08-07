"""
LLM module for CivicFlow AI.

Exports the single public function that the rest of the system uses.
"""

from .llm import extract_complaint_information

__all__ = ["extract_complaint_information"]
