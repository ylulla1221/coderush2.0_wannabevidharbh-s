"""
Vector store abstraction for CivicFlow AI Duplicate Detection.

This module wraps all interactions with the Qdrant vector database.
It exposes a narrow, backend-agnostic interface so that swapping
Qdrant for Pinecone, FAISS, or any other engine requires changes
ONLY in this file — no business logic is encoded here.

Public Functions:
    insert_complaint(complaint_id, vector, payload)
    search_similar(vector, limit)
    delete_complaint(complaint_id)
    health_check()

Design:
    - Lazy client:  The Qdrant client is created on first use.
    - Auto-collection:  The collection is created automatically if
                        it does not exist on the first write.
    - No business logic:  This layer does not interpret similarity
                          scores, classify duplicates, or manage clusters.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from .config import (
    QDRANT_COLLECTION,
    QDRANT_HOST,
    QDRANT_PORT,
    QDRANT_URL,
    QDRANT_API_KEY,
)
from .exceptions import VectorStoreError

# =============================================================================
# LOGGING
# =============================================================================

logger = logging.getLogger("civicflow.ai.duplicate.vector_store")

# =============================================================================
# SINGLETON STATE
# =============================================================================

_client_instance: Any | None = None
_client_lock: threading.Lock = threading.Lock()

# =============================================================================
# EMBEDDING DIMENSION (BGE-base-en-v1.5 produces 768-d vectors)
# =============================================================================

_VECTOR_DIMENSION: int = 768


# =============================================================================
# PRIVATE HELPERS
# =============================================================================


def _get_client() -> Any:
    """Return the singleton Qdrant client.

    Creates the client on first call. Thread-safe.
    Automatically detects whether to use Qdrant Cloud or local Qdrant.

    Returns:
        A connected QdrantClient instance.

    Raises:
        VectorStoreError: If the client cannot be created.
    """
    global _client_instance

    if _client_instance is not None:
        return _client_instance

    with _client_lock:
        if _client_instance is not None:
            return _client_instance

        try:
            from qdrant_client import QdrantClient
            import httpx
        except ImportError as exc:
            raise VectorStoreError(
                "qdrant-client or httpx is not installed. "
                "Run: pip install qdrant-client httpx"
            ) from exc

        try:
            if QDRANT_URL:
                logger.info("Connecting to Qdrant Cloud at %s", QDRANT_URL)
                _client_instance = QdrantClient(
                    url=QDRANT_URL,
                    api_key=QDRANT_API_KEY,
                )
            else:
                logger.info(
                    "Connecting to local Qdrant at %s:%d",
                    QDRANT_HOST,
                    QDRANT_PORT,
                )
                _client_instance = QdrantClient(
                    host=QDRANT_HOST,
                    port=QDRANT_PORT,
                )

            logger.info("Qdrant client initialized successfully.")
            return _client_instance

        except Exception as exc:
            raise VectorStoreError(
                f"Failed to initialize Qdrant client: {exc}"
            ) from exc


def _handle_qdrant_error(exc: Exception, context_msg: str) -> VectorStoreError:
    """Helper to classify and wrap Qdrant exceptions into VectorStoreError.
    
    Distinguishes between connection errors, authentication errors, and other API errors.
    """
    import httpx
    try:
        from qdrant_client.http.exceptions import UnexpectedResponse
    except ImportError:
        UnexpectedResponse = None

    if isinstance(exc, httpx.ConnectError):
        return VectorStoreError(f"Connection error: Unable to reach Qdrant server. {exc}")
    
    if UnexpectedResponse and isinstance(exc, UnexpectedResponse):
        if exc.status_code in (401, 403):
            return VectorStoreError(f"Authentication error: Invalid API key or unauthorized. {exc}")
        return VectorStoreError(f"API error [{exc.status_code}]: {exc}")

    return VectorStoreError(f"{context_msg}: {exc}")


def _ensure_collection() -> None:
    """Create the Qdrant collection if it does not already exist.

    Uses cosine distance to match the normalised embeddings produced
    by the embedder module.

    Raises:
        VectorStoreError: If collection creation fails.
    """
    client = _get_client()

    try:
        from qdrant_client.models import Distance, VectorParams

        collections = client.get_collections().collections
        existing_names = {c.name for c in collections}

        if QDRANT_COLLECTION in existing_names:
            logger.debug(
                "Collection '%s' already exists.",
                QDRANT_COLLECTION,
            )
            return

        logger.info(
            "Creating Qdrant collection '%s' (%d dimensions, cosine).",
            QDRANT_COLLECTION,
            _VECTOR_DIMENSION,
        )

        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(
                size=_VECTOR_DIMENSION,
                distance=Distance.COSINE,
            ),
        )

        logger.info(
            "Collection '%s' created successfully.",
            QDRANT_COLLECTION,
        )

    except VectorStoreError:
        raise
    except Exception as exc:
        raise _handle_qdrant_error(exc, f"Failed to ensure collection '{QDRANT_COLLECTION}'") from exc


# =============================================================================
# PUBLIC API
# =============================================================================


def insert_complaint(
    complaint_id: str,
    vector: list[float],
    payload: dict[str, Any],
) -> None:
    """Insert a complaint vector with metadata into the vector store.

    Automatically creates the collection on the first insert.

    Args:
        complaint_id: Unique identifier for the complaint.
        vector:       Dense embedding vector (list of floats).
        payload:      Metadata dictionary to store alongside the vector.

    Raises:
        VectorStoreError: If the upsert operation fails.
    """
    _ensure_collection()

    client = _get_client()

    try:
        from qdrant_client.models import PointStruct

        point = PointStruct(
            id=_complaint_id_to_int(complaint_id),
            vector=vector,
            payload={**payload, "complaint_id": complaint_id},
        )

        client.upsert(
            collection_name=QDRANT_COLLECTION,
            points=[point],
        )

        logger.info(
            "Inserted complaint '%s' into collection '%s'.",
            complaint_id,
            QDRANT_COLLECTION,
        )

    except VectorStoreError:
        raise
    except Exception as exc:
        raise _handle_qdrant_error(exc, f"Failed to insert complaint '{complaint_id}'") from exc


def search_similar(
    vector: list[float],
    limit: int,
) -> list[dict[str, Any]]:
    """Search the vector store for complaints similar to the given vector.

    Args:
        vector: Query embedding vector.
        limit:  Maximum number of results to return.

    Returns:
        A list of dictionaries, each containing:
            - complaint_id (str)
            - score (float): Cosine similarity score.
            - payload (dict): Stored metadata.

    Raises:
        VectorStoreError: If the search operation fails.
    """
    _ensure_collection()

    client = _get_client()

    try:
        results = client.query_points(
            collection_name=QDRANT_COLLECTION,
            query=vector,
            limit=limit,
        ).points

        matches: list[dict[str, Any]] = []

        for hit in results:
            payload = hit.payload or {}
            matches.append(
                {
                    "complaint_id": payload.get("complaint_id", ""),
                    "score": float(hit.score),
                    "payload": payload,
                }
            )

        logger.debug(
            "Search returned %d results from '%s'.",
            len(matches),
            QDRANT_COLLECTION,
        )

        return matches

    except VectorStoreError:
        raise
    except Exception as exc:
        raise _handle_qdrant_error(exc, "Similarity search failed") from exc


def delete_complaint(complaint_id: str) -> None:
    """Delete a complaint from the vector store by its ID.

    Args:
        complaint_id: Unique identifier of the complaint to delete.

    Raises:
        VectorStoreError: If the delete operation fails.
    """
    client = _get_client()

    try:
        from qdrant_client.models import PointIdsList

        client.delete(
            collection_name=QDRANT_COLLECTION,
            points_selector=PointIdsList(
                points=[_complaint_id_to_int(complaint_id)],
            ),
        )

        logger.info(
            "Deleted complaint '%s' from collection '%s'.",
            complaint_id,
            QDRANT_COLLECTION,
        )

    except VectorStoreError:
        raise
    except Exception as exc:
        raise _handle_qdrant_error(exc, f"Failed to delete complaint '{complaint_id}'") from exc


def health_check() -> dict[str, Any]:
    """Check connectivity and collection status of the vector store.

    Returns:
        A dictionary with health information:
            - status (str): "healthy" or "unhealthy".
            - host (str): Qdrant host.
            - port (int): Qdrant port.
            - collection (str): Collection name.
            - vector_count (int): Number of vectors in the collection.
            - error (str | None): Error message if unhealthy.

    Raises:
        VectorStoreError: Never — errors are captured in the response.
    """
    health: dict[str, Any] = {
        "status": "unhealthy",
        "host": QDRANT_URL if QDRANT_URL else QDRANT_HOST,
        "port": QDRANT_PORT if not QDRANT_URL else None,
        "collection": QDRANT_COLLECTION,
        "vector_count": 0,
        "error": None,
    }

    try:
        client = _get_client()

        collection_info = client.get_collection(
            collection_name=QDRANT_COLLECTION,
        )

        health["status"] = "healthy"
        health["vector_count"] = collection_info.points_count or 0

        logger.info(
            "Vector store health check passed: %d vectors.",
            health["vector_count"],
        )

    except Exception as exc:
        try:
            err = _handle_qdrant_error(exc, "Health check failed")
            health["error"] = str(err)
        except Exception:
            health["error"] = str(exc)

        logger.warning(
            "Vector store health check failed: %s",
            health["error"],
        )

    return health


# =============================================================================
# ID HASHING
# =============================================================================


def _complaint_id_to_int(complaint_id: str) -> int:
    """Convert a string complaint ID to a positive integer for Qdrant.

    Qdrant requires point IDs to be unsigned 64-bit integers or UUIDs.
    This function uses a stable hash to produce a deterministic integer
    from any string ID format (e.g., "cmp_103", "complaint-2024-001").

    Args:
        complaint_id: String complaint identifier.

    Returns:
        A positive 64-bit integer derived from the complaint ID.
    """
    import hashlib

    digest = hashlib.sha256(complaint_id.encode("utf-8")).hexdigest()

    return int(digest[:16], 16)
