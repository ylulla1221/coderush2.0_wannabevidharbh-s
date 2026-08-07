"""
Sentence embedding generator for CivicFlow AI Duplicate Detection.

This module is the SOLE interface for embedding generation in the
duplicate detection pipeline. No other file in this module should
import HuggingFace / sentence-transformers directly.

Design:
    - Lazy loading:   The model is downloaded and loaded only on the
                      first call to generate_embedding().
    - Singleton:      A single model instance is shared across all calls
                      for the lifetime of the process.
    - Thread safety:  A threading lock guards model initialisation so
                      concurrent requests never trigger parallel downloads.

Public Function:
    generate_embedding(text) → list[float]
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from .config import EMBEDDING_MODEL
from .exceptions import EmbeddingError

# =============================================================================
# LOGGING
# =============================================================================

logger = logging.getLogger("civicflow.ai.duplicate.embedder")

# =============================================================================
# SINGLETON STATE
# =============================================================================

_model_instance: Any | None = None
_model_lock: threading.Lock = threading.Lock()


# =============================================================================
# PRIVATE HELPERS
# =============================================================================


def _get_model() -> Any:
    """Return the singleton SentenceTransformer model instance.

    Downloads and initialises the model on first call. Subsequent
    calls return the cached instance. Thread-safe.

    Returns:
        A loaded SentenceTransformer model.

    Raises:
        EmbeddingError: If the model cannot be loaded.
    """
    global _model_instance

    if _model_instance is not None:
        return _model_instance

    with _model_lock:
        if _model_instance is not None:
            return _model_instance

        logger.info(
            "Loading embedding model: %s (first request — this may take a moment)",
            EMBEDDING_MODEL,
        )

        try:
            from sentence_transformers import SentenceTransformer

            _model_instance = SentenceTransformer(EMBEDDING_MODEL)

            logger.info(
                "Embedding model loaded successfully: %s",
                EMBEDDING_MODEL,
            )

            return _model_instance

        except ImportError as exc:
            raise EmbeddingError(
                "sentence-transformers is not installed. "
                "Run: pip install sentence-transformers"
            ) from exc

        except Exception as exc:
            raise EmbeddingError(
                f"Failed to load embedding model '{EMBEDDING_MODEL}': {exc}"
            ) from exc


def _validate_text(text: str) -> str:
    """Validate and normalise input text before embedding.

    Args:
        text: Raw input text.

    Returns:
        Stripped, non-empty string.

    Raises:
        EmbeddingError: If text is empty or not a string.
    """
    if not isinstance(text, str):
        raise EmbeddingError(
            f"Expected str, received {type(text).__name__}."
        )

    cleaned = text.strip()

    if not cleaned:
        raise EmbeddingError("Cannot generate embedding for empty text.")

    return cleaned


# =============================================================================
# PUBLIC API
# =============================================================================


def generate_embedding(text: str) -> list[float]:
    """Generate a sentence embedding for the given text.

    This is the ONLY public function. All other modules in
    the duplicate package call this — nothing else.

    Args:
        text: The text to embed (typically a complaint summary).

    Returns:
        A list of floats representing the dense embedding vector.

    Raises:
        EmbeddingError: If text validation or model inference fails.
    """
    validated_text = _validate_text(text)

    model = _get_model()

    try:
        logger.debug(
            "Generating embedding for text (%d chars).",
            len(validated_text),
        )

        vector = model.encode(
            validated_text,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        embedding = vector.tolist()

        logger.debug(
            "Embedding generated: %d dimensions.",
            len(embedding),
        )

        return embedding

    except Exception as exc:
        raise EmbeddingError(
            f"Model inference failed: {exc}"
        ) from exc
