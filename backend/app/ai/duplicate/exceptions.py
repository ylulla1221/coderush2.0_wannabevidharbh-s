"""
Custom exceptions for CivicFlow AI Duplicate Detection module.

Exception Hierarchy:
    DuplicateDetectionError
        ├── EmbeddingError       — Sentence embedding failures.
        └── VectorStoreError     — Vector database operation failures.

Design:
    - DuplicateDetectionError is the base for ALL duplicate module errors.
    - External callers only need to catch DuplicateDetectionError for
      a blanket handler, or individual subclasses for granular control.
    - Every exception carries a human-readable message suitable for
      structured logging.
"""

from __future__ import annotations


class DuplicateDetectionError(Exception):
    """Base exception for all duplicate detection failures.

    Attributes:
        message: Human-readable description of the failure.
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


class EmbeddingError(DuplicateDetectionError):
    """Raised when sentence embedding generation fails.

    Common causes:
        - Model download failure.
        - Invalid or empty input text.
        - Out-of-memory on the inference device.
    """

    def __init__(self, message: str) -> None:
        super().__init__(f"Embedding failure: {message}")


class VectorStoreError(DuplicateDetectionError):
    """Raised when a vector database operation fails.

    Common causes:
        - Qdrant server unreachable.
        - Collection does not exist.
        - Malformed payload or vector dimension mismatch.
    """

    def __init__(self, message: str) -> None:
        super().__init__(f"Vector store failure: {message}")
