"""ChromaDB vector store helpers for per-analysis resume search."""

from pathlib import Path
import re
from typing import Any

import chromadb


CHROMA_PATH = Path(__file__).resolve().parents[1] / "data" / "chroma"
COLLECTION_PREFIX = "resume_analysis"


def _get_client():
    """Create a local persistent Chroma client."""
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_PATH))


def _collection_name(session_id: str) -> str:
    """Build a Chroma-safe collection name from a session id."""
    safe_session_id = re.sub(r"[^a-zA-Z0-9_-]", "_", session_id).strip("_")
    if not safe_session_id:
        safe_session_id = "session"

    name = f"{COLLECTION_PREFIX}_{safe_session_id}"
    return name[:63]


def create_session_collection(session_id: str):
    """Create an isolated Chroma collection for one analysis session."""
    client = _get_client()
    collection_name = _collection_name(session_id)

    try:
        client.delete_collection(collection_name)
    except Exception:
        pass

    return client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def _chunk_value(chunk: Any, key: str, default: Any = None) -> Any:
    """Read a value from a dataclass/object chunk or a dict chunk."""
    if isinstance(chunk, dict):
        return chunk.get(key, default)
    return getattr(chunk, key, default)


def add_resume_chunks(
    collection,
    chunks,
    embeddings: list[list[float]],
) -> None:
    """Store resume chunk text, metadata, and precomputed embeddings."""
    if not chunks:
        raise ValueError("At least one resume chunk is required.")
    if len(chunks) != len(embeddings):
        raise ValueError("Chunks and embeddings must have the same length.")

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, str | int]] = []

    for index, chunk in enumerate(chunks):
        chunk_id = str(_chunk_value(chunk, "chunk_id", f"chunk_{index}"))
        chunk_text = str(_chunk_value(chunk, "text", "")).strip()
        section = _chunk_value(chunk, "section", None) or "Unknown"
        chunk_index = _chunk_value(chunk, "chunk_index", index)

        if not chunk_text:
            raise ValueError("Resume chunk text cannot be empty.")

        ids.append(chunk_id)
        documents.append(chunk_text)
        metadatas.append(
            {
                "chunk_id": chunk_id,
                "section": str(section),
                "chunk_index": int(chunk_index),
            }
        )

    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )


def _distance_to_similarity(distance: float | None) -> float:
    """Convert Chroma cosine distance to a 0-1 similarity value (1 - distance)."""
    if distance is None:
        return 0.0
    similarity = 1.0 - float(distance)
    return round(max(0.0, min(1.0, similarity)), 2)


def query_resume_chunks(
    collection,
    query_texts: list[str],
    query_embeddings: list[list[float]],
    top_k: int = 3,
) -> list[dict]:
    """Query resume chunks with job-side embeddings and return top matches."""
    if not query_texts:
        raise ValueError("At least one query text is required.")
    if len(query_texts) != len(query_embeddings):
        raise ValueError("Query texts and embeddings must have the same length.")

    chunk_count = collection.count()
    if chunk_count == 0:
        return []

    result_limit = max(1, min(top_k, chunk_count))
    results = collection.query(
        query_embeddings=query_embeddings,
        n_results=result_limit,
        include=["documents", "metadatas", "distances"],
    )

    matches: list[dict] = []
    result_ids = results.get("ids") or []
    documents = results.get("documents") or []
    metadatas = results.get("metadatas") or []
    distances = results.get("distances") or []

    for query_index, query_text in enumerate(query_texts):
        query_documents = documents[query_index] if query_index < len(documents) else []
        query_metadatas = metadatas[query_index] if query_index < len(metadatas) else []
        query_distances = distances[query_index] if query_index < len(distances) else []
        query_ids = result_ids[query_index] if query_index < len(result_ids) else []

        for match_index, resume_chunk in enumerate(query_documents):
            metadata = (
                query_metadatas[match_index]
                if match_index < len(query_metadatas)
                else {}
            ) or {}
            distance = (
                query_distances[match_index]
                if match_index < len(query_distances)
                else None
            )
            chunk_id = metadata.get("chunk_id")
            if not chunk_id and match_index < len(query_ids):
                chunk_id = query_ids[match_index]

            matches.append(
                {
                    "job_requirement": query_text,
                    "resume_chunk": resume_chunk,
                    "similarity_score": _distance_to_similarity(distance),
                    "section": metadata.get("section", "Unknown"),
                    "chunk_id": chunk_id,
                }
            )

    return matches


def delete_session_collection(session_id: str) -> None:
    """Delete one analysis session collection without removing all Chroma data."""
    client = _get_client()
    collection_name = _collection_name(session_id)

    try:
        client.delete_collection(collection_name)
    except Exception:
        pass
