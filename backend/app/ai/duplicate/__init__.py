"""
Duplicate Detection module for CivicFlow AI.

Exports the single public function that the rest of the system uses.
No external module should directly import embedder, vector_store,
or any internal component — everything routes through
`find_duplicate_complaint()`.
"""

from .duplicate_detector import find_duplicate_complaint

__all__ = ["find_duplicate_complaint"]
