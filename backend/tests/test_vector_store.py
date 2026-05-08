import uuid

import pytest

from app import vector_store
from app.chunker import ResumeChunk
from app.vector_store import (
    add_resume_chunks,
    create_session_collection,
    delete_session_collection,
    query_resume_chunks,
)


def test_vector_store_add_query_and_delete(tmp_path, monkeypatch):
    monkeypatch.setattr(vector_store, "CHROMA_PATH", tmp_path / "chroma")

    session_id = f"test_{uuid.uuid4().hex}"
    collection = create_session_collection(session_id)

    chunks = [
        ResumeChunk(
            chunk_id="chunk_0",
            text="Built Python and FastAPI backend services.",
            section="Projects",
            chunk_index=0,
        ),
        ResumeChunk(
            chunk_id="chunk_1",
            text="Designed SQL database tables and reporting queries.",
            section="Experience",
            chunk_index=1,
        ),
    ]
    embeddings = [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
    ]

    add_resume_chunks(collection, chunks, embeddings)
    matches = query_resume_chunks(
        collection,
        query_texts=["Python"],
        query_embeddings=[[1.0, 0.0, 0.0]],
        top_k=1,
    )

    assert len(matches) == 1
    assert {
        "job_requirement",
        "resume_chunk",
        "similarity_score",
        "section",
        "chunk_id",
    }.issubset(matches[0])
    assert matches[0]["job_requirement"] == "Python"
    assert "Python" in matches[0]["resume_chunk"]
    assert matches[0]["chunk_id"] == "chunk_0"
    assert isinstance(matches[0]["similarity_score"], float)

    delete_session_collection(session_id)

    with pytest.raises(Exception):
        vector_store._get_client().get_collection(
            vector_store._collection_name(session_id)
        )
