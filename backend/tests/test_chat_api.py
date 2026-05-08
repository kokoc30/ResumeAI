import urllib.error

from fastapi.testclient import TestClient

from app import main, vector_store


def sample_analysis_context():
    return {
        "match_score": 42,
        "summary": "Partial match with useful Python evidence and missing quantum requirements.",
        "matched_skills": [
            {
                "skill": "Python",
                "confidence": "high",
                "resume_evidence": "Built backend APIs with Python.",
            }
        ],
        "missing_skills": [
            {
                "skill": "Quantum Computing",
                "importance": "high",
                "suggestion": "Build honest evidence through a project or coursework.",
            }
        ],
        "resume_suggestions": [
            "Add one measurable project bullet tied to the target role."
        ],
        "top_resume_matches": [
            {
                "job_requirement": "Python",
                "resume_chunk": "Built backend APIs with Python.",
                "similarity_score": 0.77,
            }
        ],
    }


def test_chat_rejects_blank_message():
    client = TestClient(main.app)

    response = client.post(
        "/api/chat",
        json={
            "message": "   ",
            "analysis_context": sample_analysis_context(),
        },
    )

    assert response.status_code == 400
    assert "cannot be empty" in response.json()["detail"]


def test_chat_rejects_empty_analysis_context():
    client = TestClient(main.app)

    response = client.post(
        "/api/chat",
        json={
            "message": "Why is my score low?",
            "analysis_context": {},
        },
    )

    assert response.status_code == 400
    assert "Run a resume analysis first" in response.json()["detail"]


def test_chat_rejects_missing_analysis_context():
    client = TestClient(main.app)

    response = client.post(
        "/api/chat",
        json={"message": "Why is my score low?"},
    )

    assert response.status_code == 400
    assert "Run a resume analysis first" in response.json()["detail"]


def test_chat_returns_response_shape_and_uses_generator(monkeypatch):
    calls = {}

    def fake_generate_chat_response(analysis_context, user_message):
        calls["analysis_context"] = analysis_context
        calls["user_message"] = user_message
        return "Focus on honest, evidence-backed project bullets."

    monkeypatch.setattr(
        main.llm_client,
        "generate_chat_response",
        fake_generate_chat_response,
    )
    monkeypatch.setattr(main.llm_client, "is_llm_enabled", lambda: True)
    monkeypatch.setattr(main.settings, "llm_provider", "ollama")
    monkeypatch.setattr(main.settings, "ollama_mode", "local")
    monkeypatch.setattr(main.settings, "ollama_model", "qwen3:4b")

    client = TestClient(main.app)
    response = client.post(
        "/api/chat",
        json={
            "message": " Why is my score low? ",
            "analysis_context": sample_analysis_context(),
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data == {
        "answer": "Focus on honest, evidence-backed project bullets.",
        "provider": "ollama",
        "model": "qwen3:4b",
        "llm_enabled": True,
    }
    assert calls["user_message"] == "Why is my score low?"
    assert calls["analysis_context"]["match_score"] == 42


def test_chat_returns_disabled_fallback_response(monkeypatch):
    monkeypatch.setattr(main.llm_client, "is_llm_enabled", lambda: False)
    monkeypatch.setattr(
        main.llm_client,
        "generate_chat_response",
        lambda _context, _message: "Local LLM chat is disabled. Use the current analysis.",
    )

    client = TestClient(main.app)
    response = client.post(
        "/api/chat",
        json={
            "message": "What should I do first?",
            "analysis_context": sample_analysis_context(),
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"].startswith("Local LLM chat is disabled")
    assert data["llm_enabled"] is False


def test_chat_status_returns_provider_model_and_enabled(monkeypatch):
    monkeypatch.setattr(main.llm_client, "is_llm_enabled", lambda: True)
    monkeypatch.setattr(main.settings, "llm_provider", "ollama")
    monkeypatch.setattr(main.settings, "ollama_model", "qwen3:4b")

    client = TestClient(main.app)
    response = client.get("/api/chat/status")

    assert response.status_code == 200
    assert response.json() == {
        "llm_enabled": True,
        "provider": "ollama",
        "mode": "local",
        "model": "qwen3:4b",
    }


def test_chat_status_uses_lightweight_default_model_when_blank(monkeypatch):
    monkeypatch.setattr(main.llm_client, "is_llm_enabled", lambda: True)
    monkeypatch.setattr(main.settings, "llm_provider", "ollama")
    monkeypatch.setattr(main.settings, "ollama_mode", "local")
    monkeypatch.setattr(main.settings, "ollama_model", "")

    client = TestClient(main.app)
    response = client.get("/api/chat/status")

    assert response.status_code == 200
    assert response.json() == {
        "llm_enabled": True,
        "provider": "ollama",
        "mode": "local",
        "model": "llama3.2:1b",
    }


def test_chat_status_includes_cloud_mode_without_api_key(monkeypatch):
    secret_key = "secret-cloud-key"
    monkeypatch.setattr(main.llm_client, "is_llm_enabled", lambda: True)
    monkeypatch.setattr(main.settings, "llm_provider", "ollama")
    monkeypatch.setattr(main.settings, "ollama_mode", "cloud")
    monkeypatch.setattr(main.settings, "ollama_model", "llama3.2:1b")
    monkeypatch.setattr(main.settings, "ollama_api_key", secret_key)

    client = TestClient(main.app)
    response = client.get("/api/chat/status")

    assert response.status_code == 200
    data = response.json()
    assert data == {
        "llm_enabled": True,
        "provider": "ollama",
        "mode": "cloud",
        "model": "llama3.2:1b",
    }
    assert secret_key not in response.text


def test_chat_response_does_not_expose_cloud_api_key(monkeypatch):
    secret_key = "secret-cloud-key"
    monkeypatch.setattr(main.settings, "llm_enabled", True)
    monkeypatch.setattr(main.settings, "llm_provider", "ollama")
    monkeypatch.setattr(main.settings, "ollama_mode", "cloud")
    monkeypatch.setattr(main.settings, "ollama_base_url", "https://ollama.com/api")
    monkeypatch.setattr(main.settings, "ollama_model", "llama3.2:1b")
    monkeypatch.setattr(main.settings, "ollama_api_key", secret_key)

    def fake_urlopen(request, timeout):
        raise urllib.error.HTTPError(
            url="https://ollama.com/api/generate",
            code=401,
            msg="unauthorized",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(main.llm_client.urllib.request, "urlopen", fake_urlopen)

    client = TestClient(main.app)
    response = client.post(
        "/api/chat",
        json={
            "message": "What should I improve first?",
            "analysis_context": sample_analysis_context(),
        },
    )

    assert response.status_code == 200
    assert "authentication failed" in response.json()["answer"]
    assert secret_key not in response.text


def test_chat_api_does_not_break_analyze(tmp_path, monkeypatch):
    monkeypatch.setattr(vector_store, "CHROMA_PATH", tmp_path / "chroma")
    monkeypatch.setattr(
        main,
        "extract_resume_text",
        lambda _bytes, _name: (
            "Jane Doe\nSkills\nPython, FastAPI, SQL\n"
            "Built Python APIs with FastAPI and SQL databases."
        ),
    )
    monkeypatch.setattr(
        main,
        "embed_texts",
        lambda texts: [[1.0, 0.0, 0.0] for _text in texts],
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
        data={
            "job_description": (
                "We need a Python developer with FastAPI and SQL experience."
            )
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "match_score" in data
    assert "embeddings" not in data
