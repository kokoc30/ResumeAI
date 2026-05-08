import socket
import urllib.error

from app import llm_client
from app.config import Settings


def sample_analysis_context():
    return {
        "match_score": 42,
        "summary": "Partial match with strong Python evidence and missing quantum requirements.",
        "matched_skills": [
            {
                "skill": "Python",
                "confidence": "high",
                "resume_evidence": "Built backend services with Python.",
            }
        ],
        "missing_skills": [
            {
                "skill": "Quantum Computing",
                "importance": "high",
                "suggestion": "Build honest evidence through a focused project or coursework.",
            }
        ],
        "resume_suggestions": [
            "Add a measurable Python project bullet tied to the role.",
            "Do not add quantum computing unless you have real experience.",
        ],
        "top_resume_matches": [
            {
                "job_requirement": "Python",
                "resume_chunk": "Created APIs and automation scripts with Python.",
                "similarity_score": 0.78,
            }
        ],
        "embeddings": [999999, 888888],
        "raw_resume_text": "SECRET FULL RAW RESUME TEXT",
        "resume_text": "ANOTHER RAW RESUME FIELD",
    }


class FakeOllamaResponse:
    status = 200

    def __init__(self, body):
        self.body = body.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self.body


def configure_ollama(
    monkeypatch,
    *,
    enabled=True,
    provider="ollama",
    mode="local",
    base_url="http://127.0.0.1:11434",
    model="llama3.2:1b",
    api_key="",
):
    monkeypatch.setattr(llm_client.settings, "llm_enabled", enabled)
    monkeypatch.setattr(llm_client.settings, "llm_provider", provider)
    monkeypatch.setattr(llm_client.settings, "ollama_mode", mode)
    monkeypatch.setattr(llm_client.settings, "ollama_base_url", base_url)
    monkeypatch.setattr(llm_client.settings, "ollama_model", model)
    monkeypatch.setattr(llm_client.settings, "ollama_api_key", api_key)


def test_settings_default_ollama_model_is_lightweight(monkeypatch):
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)

    settings = Settings(_env_file=None)

    assert settings.ollama_model == "llama3.2:1b"


def test_settings_default_ollama_mode_is_local(monkeypatch):
    monkeypatch.delenv("OLLAMA_MODE", raising=False)

    settings = Settings(_env_file=None)

    assert settings.ollama_mode == "local"


def test_settings_env_override_for_model_still_works(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:4b")

    settings = Settings(_env_file=None)

    assert settings.ollama_model == "qwen3:4b"


def test_is_llm_enabled_false_when_disabled(monkeypatch):
    monkeypatch.setattr(llm_client.settings, "llm_enabled", False)
    monkeypatch.setattr(llm_client.settings, "llm_provider", "ollama")

    assert llm_client.is_llm_enabled() is False


def test_is_llm_enabled_true_only_for_ollama(monkeypatch):
    monkeypatch.setattr(llm_client.settings, "llm_enabled", "true")
    monkeypatch.setattr(llm_client.settings, "llm_provider", "openai")

    assert llm_client.is_llm_enabled() is False

    monkeypatch.setattr(llm_client.settings, "llm_provider", "ollama")
    assert llm_client.is_llm_enabled() is True


def test_get_ollama_mode_defaults_to_local_when_missing(monkeypatch):
    monkeypatch.setattr(llm_client.settings, "ollama_mode", "")

    assert llm_client.get_ollama_mode() == "local"


def test_local_mode_generate_url_normalizes_host_base(monkeypatch):
    configure_ollama(
        monkeypatch,
        mode="local",
        base_url="http://127.0.0.1:11434",
    )

    assert (
        llm_client.get_ollama_generate_url()
        == "http://127.0.0.1:11434/api/generate"
    )


def test_generate_url_normalizes_api_base(monkeypatch):
    configure_ollama(
        monkeypatch,
        mode="cloud",
        base_url="https://ollama.com/api",
        api_key="test-key",
    )

    assert llm_client.get_ollama_generate_url() == "https://ollama.com/api/generate"


def test_generate_url_normalizes_cloud_host_base(monkeypatch):
    configure_ollama(
        monkeypatch,
        mode="cloud",
        base_url="https://ollama.com",
        api_key="test-key",
    )

    assert llm_client.get_ollama_generate_url() == "https://ollama.com/api/generate"


def test_cloud_mode_uses_cloud_default_base_url_when_blank(monkeypatch):
    configure_ollama(
        monkeypatch,
        mode="cloud",
        base_url="",
        api_key="test-key",
    )

    assert llm_client.get_ollama_generate_url() == "https://ollama.com/api/generate"


def test_local_mode_does_not_send_authorization_header(monkeypatch):
    configure_ollama(
        monkeypatch,
        mode="local",
        api_key="should-not-be-sent",
    )

    headers = llm_client.get_ollama_headers()

    assert headers["Content-Type"] == "application/json"
    assert "Authorization" not in headers


def test_cloud_mode_sends_authorization_header(monkeypatch):
    configure_ollama(
        monkeypatch,
        mode="cloud",
        base_url="https://ollama.com/api",
        api_key="test-cloud-key",
    )

    headers = llm_client.get_ollama_headers()

    assert headers["Content-Type"] == "application/json"
    assert headers["Authorization"] == "Bearer test-cloud-key"


def test_build_chat_prompt_includes_core_analysis_fields():
    prompt = llm_client.build_chat_prompt(
        sample_analysis_context(),
        "How should I improve this resume?",
    )

    assert "Match score: 42" in prompt
    assert "Python" in prompt
    assert "Quantum Computing" in prompt
    assert "Add a measurable Python project bullet" in prompt
    assert "Created APIs and automation scripts with Python" in prompt
    assert "Do not invent projects" in prompt


def test_build_chat_prompt_enforces_concise_format_rules():
    prompt = llm_client.build_chat_prompt(
        sample_analysis_context(),
        "What should I improve first?",
    )

    assert "3-5 bullets" in prompt
    assert "one short direct answer sentence" in prompt
    assert "no markdown tables" in prompt.lower()
    assert "no numbered outlines" in prompt.lower()


def test_build_chat_prompt_forbids_invented_metrics_and_skills():
    prompt = llm_client.build_chat_prompt(
        sample_analysis_context(),
        "How can I tailor my resume?",
    )

    assert "Do not invent or assume exact metrics" in prompt
    assert "add real measurable results if you have them" in prompt
    assert "Java" in prompt and "React" in prompt
    assert "Do not say the user has" in prompt
    assert "Do not tell the user to claim skills they do not have" in prompt


def test_build_chat_prompt_hides_internals_unless_asked():
    prompt = llm_client.build_chat_prompt(
        sample_analysis_context(),
        "Why is my score low?",
    )

    assert "ChromaDB" in prompt
    assert "embeddings" in prompt
    assert "unless the user explicitly asks" in prompt


def test_build_chat_prompt_sections_are_structured_and_capped():
    context = sample_analysis_context()
    context["matched_skills"] = [
        {"skill": f"Skill{i}", "confidence": "high"} for i in range(20)
    ]
    context["missing_skills"] = [
        {"skill": f"Gap{i}", "importance": "high", "suggestion": "Build evidence."}
        for i in range(20)
    ]
    context["resume_suggestions"] = [f"Suggestion {i}" for i in range(20)]
    context["top_resume_matches"] = [
        {
            "job_requirement": f"Req {i}",
            "resume_chunk": "x" * 1000,
            "similarity_score": 0.5,
        }
        for i in range(10)
    ]

    prompt = llm_client.build_chat_prompt(context, "Help me prioritize.")

    assert "Matched skills" in prompt
    assert "Missing skills" in prompt
    assert "Resume suggestions" in prompt or "Action steps" in prompt
    assert "Resume evidence snippets" in prompt
    # Hard caps respected
    assert prompt.count("- Skill") <= llm_client.MAX_MATCHED_SKILLS
    assert prompt.count("- Gap") <= llm_client.MAX_MISSING_SKILLS
    assert prompt.count("- Suggestion ") <= llm_client.MAX_SUGGESTIONS
    assert prompt.count("evidence snippet:") <= llm_client.MAX_EVIDENCE_ITEMS
    # Long evidence chunks are trimmed (no 1000-x runs survive)
    assert "x" * (llm_client.MAX_EVIDENCE_CHARS + 10) not in prompt


def test_build_chat_prompt_preserves_missing_skill_priority():
    context = sample_analysis_context()
    context["missing_skills"] = [
        {"skill": "Kubernetes", "priority": "critical", "suggestion": "Try a small lab."}
    ]

    prompt = llm_client.build_chat_prompt(context, "What matters most?")

    assert "Kubernetes" in prompt
    assert "critical" in prompt


def test_build_chat_prompt_does_not_include_raw_embedding_values():
    prompt = llm_client.build_chat_prompt(
        sample_analysis_context(),
        "Can you explain the gaps?",
    )

    assert "999999" not in prompt
    assert "888888" not in prompt


def test_build_chat_prompt_does_not_include_raw_resume_text_fields():
    prompt = llm_client.build_chat_prompt(
        sample_analysis_context(),
        "Can you explain the gaps?",
    )

    assert "SECRET FULL RAW RESUME TEXT" not in prompt
    assert "ANOTHER RAW RESUME FIELD" not in prompt


def test_call_ollama_success_response_is_parsed(monkeypatch):
    configure_ollama(monkeypatch)

    def fake_urlopen(request, timeout):
        return FakeOllamaResponse('{"response": "Use stronger project evidence."}')

    monkeypatch.setattr(llm_client.urllib.request, "urlopen", fake_urlopen)

    response = llm_client.call_ollama("Prompt text")

    assert response == "Use stronger project evidence."


def test_call_ollama_connection_error_is_friendly(monkeypatch):
    configure_ollama(monkeypatch)

    def fake_urlopen(request, timeout):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(llm_client.urllib.request, "urlopen", fake_urlopen)

    response = llm_client.call_ollama("Prompt text")

    assert "Ollama is not running" in response


def test_call_ollama_timeout_is_friendly(monkeypatch):
    configure_ollama(monkeypatch)

    def fake_urlopen(request, timeout):
        raise socket.timeout("timed out")

    monkeypatch.setattr(llm_client.urllib.request, "urlopen", fake_urlopen)

    response = llm_client.call_ollama("Prompt text")

    assert "took longer" in response


def test_call_ollama_http_error_is_friendly(monkeypatch):
    configure_ollama(monkeypatch)

    def fake_urlopen(request, timeout):
        raise urllib.error.HTTPError(
            url="http://127.0.0.1:11434/api/generate",
            code=500,
            msg="server error",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(llm_client.urllib.request, "urlopen", fake_urlopen)

    response = llm_client.call_ollama("Prompt text")

    assert "HTTP 500" in response


def test_call_ollama_uses_normalized_url_and_local_headers(monkeypatch):
    configure_ollama(
        monkeypatch,
        mode="local",
        base_url="http://127.0.0.1:11434/api/",
        api_key="should-not-be-sent",
    )
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        return FakeOllamaResponse('{"response": "Local answer."}')

    monkeypatch.setattr(llm_client.urllib.request, "urlopen", fake_urlopen)

    response = llm_client.call_ollama("Prompt text")

    assert response == "Local answer."
    assert captured["url"] == "http://127.0.0.1:11434/api/generate"
    assert captured["authorization"] is None


def test_call_ollama_sends_cloud_authorization_header(monkeypatch):
    configure_ollama(
        monkeypatch,
        mode="cloud",
        base_url="https://ollama.com/api",
        api_key="test-cloud-key",
    )
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        return FakeOllamaResponse('{"response": "Cloud answer."}')

    monkeypatch.setattr(llm_client.urllib.request, "urlopen", fake_urlopen)

    response = llm_client.call_ollama("Prompt text")

    assert response == "Cloud answer."
    assert captured["url"] == "https://ollama.com/api/generate"
    assert captured["authorization"] == "Bearer test-cloud-key"


def test_cloud_mode_missing_api_key_returns_friendly_message(monkeypatch):
    configure_ollama(
        monkeypatch,
        mode="cloud",
        base_url="https://ollama.com/api",
        api_key="",
    )

    response = llm_client.generate_chat_response(
        sample_analysis_context(),
        "What should I improve first?",
    )

    assert "Cloud AI is enabled" in response
    assert "OLLAMA_API_KEY is missing" in response


def test_cloud_auth_error_returns_friendly_message_without_key(monkeypatch):
    secret_key = "secret-test-key"
    configure_ollama(
        monkeypatch,
        mode="cloud",
        base_url="https://ollama.com/api",
        api_key=secret_key,
    )

    def fake_urlopen(request, timeout):
        raise urllib.error.HTTPError(
            url="https://ollama.com/api/generate",
            code=401,
            msg="unauthorized",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(llm_client.urllib.request, "urlopen", fake_urlopen)

    response = llm_client.call_ollama("Prompt text")

    assert response == "Ollama Cloud authentication failed. Check your OLLAMA_API_KEY."
    assert secret_key not in response


def test_cloud_forbidden_error_returns_friendly_auth_message(monkeypatch):
    configure_ollama(
        monkeypatch,
        mode="cloud",
        base_url="https://ollama.com/api",
        api_key="test-cloud-key",
    )

    def fake_urlopen(request, timeout):
        raise urllib.error.HTTPError(
            url="https://ollama.com/api/generate",
            code=403,
            msg="forbidden",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(llm_client.urllib.request, "urlopen", fake_urlopen)

    response = llm_client.call_ollama("Prompt text")

    assert "authentication failed" in response


def test_cloud_model_not_available_error_is_friendly(monkeypatch):
    configure_ollama(
        monkeypatch,
        mode="cloud",
        base_url="https://ollama.com/api",
        api_key="test-cloud-key",
    )

    def fake_urlopen(request, timeout):
        raise urllib.error.HTTPError(
            url="https://ollama.com/api/generate",
            code=404,
            msg="not found",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(llm_client.urllib.request, "urlopen", fake_urlopen)

    response = llm_client.call_ollama("Prompt text")

    assert response == "The configured Ollama model is not available for this account or endpoint."


def test_cloud_rate_limit_error_is_friendly(monkeypatch):
    configure_ollama(
        monkeypatch,
        mode="cloud",
        base_url="https://ollama.com/api",
        api_key="test-cloud-key",
    )

    def fake_urlopen(request, timeout):
        raise urllib.error.HTTPError(
            url="https://ollama.com/api/generate",
            code=429,
            msg="too many requests",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(llm_client.urllib.request, "urlopen", fake_urlopen)

    response = llm_client.call_ollama("Prompt text")

    assert "rate limit reached" in response


def test_generate_chat_response_uses_fallback_when_disabled(monkeypatch):
    monkeypatch.setattr(llm_client, "is_llm_enabled", lambda: False)

    response = llm_client.generate_chat_response(
        sample_analysis_context(),
        "What should I do first?",
    )

    assert "Local LLM chat is disabled" in response
    assert "Quantum Computing" in response


def test_generate_chat_response_calls_ollama_when_enabled(monkeypatch):
    called = {}

    def fake_call_ollama(prompt):
        called["prompt"] = prompt
        return "LLM answer"

    monkeypatch.setattr(llm_client, "is_llm_enabled", lambda: True)
    monkeypatch.setattr(llm_client, "call_ollama", fake_call_ollama)

    response = llm_client.generate_chat_response(
        sample_analysis_context(),
        "What should I do first?",
    )

    assert response == "LLM answer"
    assert "What should I do first?" in called["prompt"]


def test_generate_chat_response_validates_blank_message():
    response = llm_client.generate_chat_response(sample_analysis_context(), "  ")

    assert "Please enter a question" in response


def test_generate_chat_response_requires_analysis_context():
    response = llm_client.generate_chat_response({}, "What should I do first?")

    assert "Run a resume analysis first" in response


def test_cloud_success_response_with_done_true(monkeypatch):
    configure_ollama(
        monkeypatch,
        mode="cloud",
        base_url="https://ollama.com/api",
        api_key="test-cloud-key",
        model="ministral-3:3b",
    )

    def fake_urlopen(request, timeout):
        return FakeOllamaResponse(
            '{"model": "ministral-3:3b", "response": "Hello!", "done": true}'
        )

    monkeypatch.setattr(llm_client.urllib.request, "urlopen", fake_urlopen)

    response = llm_client.call_ollama("Say hello.")

    assert response == "Hello!"


def test_cloud_empty_response_returns_cloud_specific_message(monkeypatch):
    configure_ollama(
        monkeypatch,
        mode="cloud",
        base_url="https://ollama.com/api",
        api_key="test-cloud-key",
    )

    def fake_urlopen(request, timeout):
        return FakeOllamaResponse(
            '{"model": "ministral-3:3b", "response": "", "done": true}'
        )

    monkeypatch.setattr(llm_client.urllib.request, "urlopen", fake_urlopen)

    response = llm_client.call_ollama("Prompt text")

    assert "Cloud" in response
    assert "empty response" in response.lower()
    assert "local setup" not in response.lower()


def test_cloud_generic_exception_does_not_mention_local_setup(monkeypatch):
    configure_ollama(
        monkeypatch,
        mode="cloud",
        base_url="https://ollama.com/api",
        api_key="test-cloud-key",
    )

    def fake_urlopen(request, timeout):
        raise RuntimeError("unexpected network layer error")

    monkeypatch.setattr(llm_client.urllib.request, "urlopen", fake_urlopen)

    response = llm_client.call_ollama("Prompt text")

    assert "Cloud" in response
    assert "local setup" not in response.lower()
    assert "local LLM" not in response


def test_call_ollama_preserves_bullet_line_breaks(monkeypatch):
    configure_ollama(monkeypatch)

    bulletted = (
        "Focus on what is already strong.\\n"
        "- Add measurable Python results you can verify.\\n"
        "- Prioritize the highest-impact missing skills.\\n"
    )

    def fake_urlopen(request, timeout):
        return FakeOllamaResponse('{"response": "' + bulletted + '"}')

    monkeypatch.setattr(llm_client.urllib.request, "urlopen", fake_urlopen)

    response = llm_client.call_ollama("Prompt text")

    assert "\n- Add measurable" in response
    assert "\n- Prioritize the highest-impact" in response


def test_clean_chat_response_passes_short_response_unchanged():
    text = "Focus on Python evidence first.\n- Add a measurable bullet.\n- Skip Java."
    assert llm_client.clean_chat_response(text) == text


def test_clean_chat_response_collapses_excessive_blank_lines():
    text = "Line one.\n\n\n\nLine two."
    cleaned = llm_client.clean_chat_response(text)
    assert "\n\n\n" not in cleaned
    assert "Line one." in cleaned and "Line two." in cleaned


def test_clean_chat_response_truncates_long_response_with_suffix():
    long_text = (
        "Direct answer sentence. "
        + ("This is a long sentence describing further details. " * 200)
    )
    cleaned = llm_client.clean_chat_response(long_text, max_chars=300)

    assert len(cleaned) <= 300 + len(llm_client.CHAT_RESPONSE_TRUNCATION_SUFFIX) + 10
    assert cleaned.endswith(llm_client.CHAT_RESPONSE_TRUNCATION_SUFFIX)
    # Did not cut mid-word at the boundary
    head = cleaned.split("\n\n")[0]
    assert not head.endswith("sente") and not head.endswith("descr")


def test_clean_chat_response_handles_empty_input():
    assert llm_client.clean_chat_response("") == ""


def test_generate_chat_response_applies_cleaner_when_enabled(monkeypatch):
    long_text = "Answer. " + ("More detail goes here. " * 500)

    monkeypatch.setattr(llm_client, "is_llm_enabled", lambda: True)
    monkeypatch.setattr(llm_client, "call_ollama", lambda _prompt: long_text)

    response = llm_client.generate_chat_response(
        sample_analysis_context(),
        "What should I improve first?",
    )

    assert len(response) <= llm_client.MAX_CHAT_RESPONSE_CHARS + len(
        llm_client.CHAT_RESPONSE_TRUNCATION_SUFFIX
    ) + 10
    assert response.endswith(llm_client.CHAT_RESPONSE_TRUNCATION_SUFFIX)


def test_build_chat_prompt_never_embeds_api_key(monkeypatch):
    secret_key = "secret-cloud-key-12345"
    configure_ollama(
        monkeypatch,
        mode="cloud",
        base_url="https://ollama.com/api",
        api_key=secret_key,
    )

    prompt = llm_client.build_chat_prompt(
        sample_analysis_context(),
        "What should I improve first?",
    )

    assert secret_key not in prompt
