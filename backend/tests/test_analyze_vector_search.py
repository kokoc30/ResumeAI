from fastapi.testclient import TestClient

from app import main, vector_store


def _fake_resume_text() -> str:
    return (
        "Jane Doe\n"
        "Software Engineer\n\n"
        "Skills\n"
        "Python, FastAPI, SQL, Docker, PostgreSQL\n\n"
        "Experience\n"
        "Built Python and FastAPI backend services with SQL databases. "
        "Packaged applications with Docker for repeatable local development."
    )


def _fake_embed_texts(texts: list[str]) -> list[list[float]]:
    vectors = []
    for text in texts:
        lower_text = text.lower()
        if "python" in lower_text or "fastapi" in lower_text:
            vectors.append([1.0, 0.0, 0.0])
        elif "sql" in lower_text or "postgresql" in lower_text:
            vectors.append([0.0, 1.0, 0.0])
        elif "docker" in lower_text:
            vectors.append([0.0, 0.0, 1.0])
        else:
            vectors.append([0.3, 0.3, 0.3])
    return vectors


def test_analyze_returns_vector_matches_without_raw_embeddings(tmp_path, monkeypatch):
    monkeypatch.setattr(vector_store, "CHROMA_PATH", tmp_path / "chroma")
    monkeypatch.setattr(main, "extract_resume_text", lambda _bytes, _name: _fake_resume_text())
    monkeypatch.setattr(main, "embed_texts", _fake_embed_texts)

    client = TestClient(main.app)
    response = client.post(
        "/api/analyze",
        files={
            "resume_file": (
                "resume.pdf",
                b"fake pdf bytes; parser is monkeypatched",
                "application/pdf",
            )
        },
        data={
            "job_description": (
                "We are looking for a Python backend developer with FastAPI, "
                "SQL, Docker, and AWS experience."
            )
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["top_resume_matches"]
    first_match = data["top_resume_matches"][0]
    assert "job_requirement" in first_match
    assert "resume_chunk" in first_match
    assert "similarity_score" in first_match
    assert isinstance(first_match["similarity_score"], float)
    assert first_match["similarity_score"] >= 0.35

    assert isinstance(data["match_score"], int)
    assert 0 <= data["match_score"] <= 100
    assert "estimated score" in data["summary"]
    assert "temporary" not in data["summary"].lower()
    assert "will be added later" not in data["summary"].lower()
    assert data["resume_suggestions"]
    assert "fake" not in " ".join(data["resume_suggestions"]).lower()

    assert "embeddings" not in data
    assert "resume_embeddings" not in data
    assert "job_embeddings" not in data
    assert "resume_text" not in data


# ---------------------------------------------------------------------------
# Specialized-role example: a Python/C++/ML resume against a quantum/compiler
# /HPC job. The response should include Python (and C++) as matched, surface
# specialized requirements as missing, and not score the role as a strong
# match purely on broad overlap.
# ---------------------------------------------------------------------------


def _specialized_resume_text() -> str:
    return (
        "John Smith\n"
        "Computer Science Student\n\n"
        "Skills\n"
        "Python, C++, C, JavaScript, Assembly, Git, Linux, TensorFlow, "
        "PyTorch, NumPy, Pandas, scikit-learn, OpenCV.\n\n"
        "Projects\n"
        "Built CNN-based image classifiers in PyTorch and TensorFlow. "
        "Implemented data pipelines in Python and explored deep learning "
        "for computer vision tasks. Worked on Arduino IoT projects in "
        "embedded C++."
    )


def _specialized_embed_texts(texts: list[str]) -> list[list[float]]:
    vectors = []
    for text in texts:
        lower_text = text.lower()
        if "python" in lower_text or "c++" in lower_text:
            vectors.append([1.0, 0.0, 0.0])
        elif "machine" in lower_text or "deep learning" in lower_text:
            vectors.append([0.5, 0.5, 0.0])
        else:
            vectors.append([0.1, 0.1, 0.1])
    return vectors


def test_analyze_specialized_quantum_role(tmp_path, monkeypatch):
    monkeypatch.setattr(vector_store, "CHROMA_PATH", tmp_path / "chroma")
    monkeypatch.setattr(
        main, "extract_resume_text", lambda _bytes, _name: _specialized_resume_text()
    )
    monkeypatch.setattr(main, "embed_texts", _specialized_embed_texts)

    job_description = (
        "Google Quantum AI Software Engineer.\n\n"
        "Minimum qualifications:\n"
        "- BS in Computer Science or equivalent\n"
        "- Strong proficiency in C++ and Python\n"
        "- Experience with software systems and compiler architecture\n"
        "- Background in quantum computing and quantum error correction\n\n"
        "Preferred qualifications:\n"
        "- Experience with high-performance computing or HPC workloads\n"
        "- Knowledge of GPU programming, CUDA, FPGA, or DSP\n"
        "- Familiarity with graph algorithms and weighted perfect matching\n"
        "- Kernel development, driver development, or concurrency\n"
        "- Logic synthesis or quantum compiler experience"
    )

    client = TestClient(main.app)
    response = client.post(
        "/api/analyze",
        files={
            "resume_file": (
                "resume.pdf",
                b"fake pdf bytes; parser is monkeypatched",
                "application/pdf",
            )
        },
        data={"job_description": job_description},
    )

    assert response.status_code == 200
    data = response.json()

    matched_names = {item["skill"] for item in data["matched_skills"]}
    missing_names = {item["skill"] for item in data["missing_skills"]}

    # Resume mentions Python and C++ — both should be matched.
    assert "Python" in matched_names
    assert "C++" in matched_names

    # Several specialized requirements must surface as missing.
    expected_missing_any = {
        "Compiler Architecture",
        "Quantum Computing",
        "Quantum Error Correction",
        "Quantum Compiler",
        "High-Performance Computing",
        "Concurrency",
        "Graph Algorithms",
        "FPGA",
        "DSP",
        "GPU Programming",
        "Kernel Development",
        "Driver Development",
        "Logic Synthesis",
    }
    overlap = expected_missing_any & missing_names
    assert len(overlap) >= 4, f"expected several specialized missing skills, got {missing_names}"

    # NLP must not be the only or first missing skill.
    if missing_names:
        first_missing = data["missing_skills"][0]["skill"]
        assert first_missing != "NLP"

    # High-priority missing skills should be surfaced first.
    importance_order = ["high", "medium", "low"]
    seen_levels = [item["importance"] for item in data["missing_skills"]]
    seen_indices = [importance_order.index(lvl) for lvl in seen_levels if lvl in importance_order]
    assert seen_indices == sorted(seen_indices)

    # Score should be partial/low, not a strong match.
    assert isinstance(data["match_score"], int)
    assert 0 <= data["match_score"] <= 100
    assert data["match_score"] < 75

    # Privacy contract still holds.
    assert "embeddings" not in data
    assert "resume_embeddings" not in data
    assert "job_embeddings" not in data
    assert "resume_text" not in data
