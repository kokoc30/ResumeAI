"""Optional Ollama LLM client helpers for resume analysis chat.

This module intentionally does not expose an API route. It prepares safe,
structured prompts and calls Ollama when the feature is enabled.
"""

from __future__ import annotations

import json
import logging
import socket
import urllib.error
import urllib.request
from typing import Any

from app.config import settings

_log = logging.getLogger(__name__)


MAX_MATCHED_SKILLS = 8
MAX_MISSING_SKILLS = 8
MAX_SUGGESTIONS = 5
MAX_EVIDENCE_ITEMS = 3
MAX_TEXT_CHARS = 700
MAX_EVIDENCE_CHARS = 400
MAX_USER_MESSAGE_CHARS = 1200
MAX_CHAT_RESPONSE_CHARS = 1400
CHAT_RESPONSE_TRUNCATION_SUFFIX = (
    "Ask me to focus on one section if you want more detail."
)
LOCAL_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
CLOUD_OLLAMA_BASE_URL = "https://ollama.com/api"
CLOUD_MISSING_API_KEY_MESSAGE = (
    "Cloud AI is enabled, but OLLAMA_API_KEY is missing. "
    "Add it to backend/.env or switch OLLAMA_MODE=local."
)


def _to_plain_data(value: Any) -> Any:
    """Convert Pydantic models and nested values into plain Python data."""
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return {str(key): _to_plain_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_plain_data(item) for item in value]
    return value


def _normalize_text(value: Any, max_chars: int = MAX_TEXT_CHARS) -> str:
    """Return single-line text capped to a safe display/prompt length."""
    text = " ".join(str(value or "").split())
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 3].rstrip()}..."


def _normalize_response_text(value: Any, max_chars: int = 4000) -> str:
    """Normalize an LLM response while preserving line breaks (for bullets)."""
    text = str(value or "")
    lines = [line.rstrip() for line in text.splitlines()]
    cleaned = "\n".join(lines).strip()
    while "\n\n\n" in cleaned:
        cleaned = cleaned.replace("\n\n\n", "\n\n")
    if len(cleaned) <= max_chars:
        return cleaned
    return f"{cleaned[: max_chars - 3].rstrip()}..."


def clean_chat_response(
    response: str,
    max_chars: int = MAX_CHAT_RESPONSE_CHARS,
) -> str:
    """Trim, collapse blank lines, and cap chat replies for the popup UI."""
    if not response:
        return response
    text = str(response).strip()
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    if len(text) <= max_chars:
        return text

    cutoff = text[:max_chars]
    soft_floor = int(max_chars * 0.6)
    for marker in ("\n\n", "\n", ". ", " "):
        idx = cutoff.rfind(marker)
        if idx >= soft_floor:
            cutoff = cutoff[:idx]
            break
    cutoff = cutoff.rstrip(" \t\n.,;:-")
    return f"{cutoff}\n\n{CHAT_RESPONSE_TRUNCATION_SUFFIX}"


def _normalize_bool(value: Any) -> bool:
    """Parse common truthy values without raising on invalid input."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    if isinstance(value, int):
        return value == 1
    return False


def _get_timeout_seconds() -> int:
    """Return a safe positive timeout value."""
    try:
        timeout = int(getattr(settings, "llm_timeout_seconds", 60))
    except (TypeError, ValueError):
        return 60
    return timeout if timeout > 0 else 60


def get_ollama_mode() -> str:
    """Return the supported Ollama mode, defaulting to local."""
    mode = str(getattr(settings, "ollama_mode", "") or "local").strip().lower()
    return mode if mode in {"local", "cloud"} else "local"


def _get_ollama_base_url() -> str:
    """Return the effective Ollama base URL for the configured mode."""
    base_url = str(getattr(settings, "ollama_base_url", "") or "").strip()
    if base_url:
        return base_url
    if get_ollama_mode() == "cloud":
        return CLOUD_OLLAMA_BASE_URL
    return LOCAL_OLLAMA_BASE_URL


def get_ollama_generate_url() -> str:
    """Return a normalized Ollama generate endpoint URL."""
    base_url = _get_ollama_base_url().rstrip("/")
    if base_url.endswith("/api"):
        return f"{base_url}/generate"
    return f"{base_url}/api/generate"


def get_ollama_headers() -> dict[str, str]:
    """Return non-logging request headers for the configured Ollama mode."""
    headers = {"Content-Type": "application/json"}
    api_key = str(getattr(settings, "ollama_api_key", "") or "").strip()
    if get_ollama_mode() == "cloud" and api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def validate_ollama_config() -> str | None:
    """Return a friendly configuration error, or None when usable."""
    if not is_llm_enabled():
        return None

    api_key = str(getattr(settings, "ollama_api_key", "") or "").strip()
    if get_ollama_mode() == "cloud" and not api_key:
        return CLOUD_MISSING_API_KEY_MESSAGE
    return None


def _format_skill_items(items: list[Any], fields: tuple[str, ...], limit: int) -> list[str]:
    """Format skill-like dictionaries without exposing unapproved fields."""
    formatted: list[str] = []
    for raw_item in items[:limit]:
        item = _to_plain_data(raw_item)
        if isinstance(item, str):
            formatted.append(f"- {_normalize_text(item, 160)}")
            continue
        if not isinstance(item, dict):
            continue

        parts: list[str] = []
        skill = _normalize_text(item.get("skill") or item.get("name"), 120)
        if skill:
            parts.append(skill)
        for field in fields:
            value = _normalize_text(item.get(field), 180)
            if value:
                label = field.replace("_", " ")
                parts.append(f"{label}: {value}")
        if parts:
            formatted.append(f"- {' | '.join(parts)}")
    return formatted


def _format_string_items(items: list[Any], limit: int) -> list[str]:
    """Format a simple list of strings."""
    return [
        f"- {_normalize_text(item, 220)}"
        for item in items[:limit]
        if _normalize_text(item, 220)
    ]


def _format_evidence_items(items: list[Any]) -> list[str]:
    """Format selected semantic evidence snippets only."""
    formatted: list[str] = []
    for raw_item in items[:MAX_EVIDENCE_ITEMS]:
        item = _to_plain_data(raw_item)
        if not isinstance(item, dict):
            continue

        requirement = _normalize_text(
            item.get("job_requirement") or item.get("requirement"),
            180,
        )
        snippet = _normalize_text(
            item.get("resume_chunk")
            or item.get("resume_snippet")
            or item.get("evidence"),
            MAX_EVIDENCE_CHARS,
        )
        similarity = item.get("similarity_score")

        parts: list[str] = []
        if requirement:
            parts.append(f"requirement: {requirement}")
        if similarity is not None:
            parts.append(f"similarity: {similarity}")
        if snippet:
            parts.append(f"evidence snippet: {snippet}")
        if parts:
            formatted.append(f"- {' | '.join(parts)}")
    return formatted


def is_llm_enabled() -> bool:
    """Return True only when the Ollama LLM feature is enabled."""
    enabled = _normalize_bool(getattr(settings, "llm_enabled", False))
    provider = str(getattr(settings, "llm_provider", "") or "").strip().lower()
    return enabled and provider == "ollama"


def build_chat_prompt(analysis_context: dict, user_message: str) -> str:
    """Build a safe, concise prompt using structured analysis context only."""
    context = _to_plain_data(analysis_context) if analysis_context else {}
    if not isinstance(context, dict):
        context = {}

    safe_user_message = _normalize_text(user_message, MAX_USER_MESSAGE_CHARS)
    sections: list[str] = [
        "You are a concise resume improvement assistant for ResumeMatch AI.",
        "",
        "Response format (strict):",
        "- Start with one short direct answer sentence.",
        "- Then use 3-5 bullets max. Each bullet is 1-2 short sentences.",
        "- Optional final sentence with the single best next step.",
        "- No long paragraphs, no numbered outlines, no markdown tables.",
        "- Keep the entire reply small enough to fit a chat popup.",
        "- Prioritize the top 1-3 highest-impact improvements only.",
        "",
        "Honesty rules (strict):",
        "- Use ONLY the analysis context below. If a fact is not in the context, do not state it.",
        "- Do not invent projects, employers, dates, job titles, or experience.",
        "- Do not invent or assume exact metrics (no fabricated percentages, throughput, accuracy, user counts, dollar amounts, or years).",
        "- Only suggest adding metrics if the resume evidence already contains them. If metrics are missing, say: \"add real measurable results if you have them.\"",
        "- Do not say the user has Java, C, C++, React, TypeScript, or any tool/framework unless it appears in matched skills or resume evidence.",
        "- Do not tell the user to claim skills they do not have. If a skill is missing, suggest honest ways to build evidence (small project, coursework, practice).",
        "- If you give example wording, prefix it with \"Example:\" and use placeholders like [your metric] instead of fabricated numbers.",
        "- If the context does not support an answer, briefly say what is missing instead of guessing.",
        "- Do not generic-advise: every bullet must reference the provided context.",
        "- Do not reveal embeddings, raw resume text, raw job description, file paths, API keys, or internals like ChromaDB or RAG unless the user explicitly asks.",
        "",
        "Analysis context:",
    ]

    match_score = context.get("match_score")
    if match_score is not None:
        sections.append(f"Match score: {_normalize_text(match_score, 40)}")

    summary = _normalize_text(context.get("summary"), MAX_TEXT_CHARS)
    if summary:
        sections.append(f"Summary: {summary}")

    for key, label in (
        ("job_summary", "Job summary"),
        ("role_summary", "Role summary"),
        ("job_requirements", "Job requirements"),
    ):
        value = context.get(key)
        if isinstance(value, list):
            lines = _format_string_items(value, MAX_SUGGESTIONS)
            if lines:
                sections.append(f"{label}:")
                sections.extend(lines)
        else:
            text = _normalize_text(value, MAX_TEXT_CHARS)
            if text:
                sections.append(f"{label}: {text}")

    matched = context.get("matched_skills")
    if isinstance(matched, list):
        lines = _format_skill_items(
            matched,
            ("confidence", "resume_evidence"),
            MAX_MATCHED_SKILLS,
        )
        if lines:
            sections.append(f"Matched skills (top {MAX_MATCHED_SKILLS}):")
            sections.extend(lines)

    missing = context.get("missing_skills")
    if isinstance(missing, list):
        lines = _format_skill_items(
            missing,
            ("importance", "priority", "suggestion"),
            MAX_MISSING_SKILLS,
        )
        if lines:
            sections.append(f"Missing skills (top {MAX_MISSING_SKILLS}, priority preserved):")
            sections.extend(lines)

    for key, label in (
        ("resume_suggestions", "Resume suggestions"),
        ("action_steps", "Action steps"),
    ):
        value = context.get(key)
        if isinstance(value, list):
            lines = _format_string_items(value, MAX_SUGGESTIONS)
            if lines:
                sections.append(f"{label} (max {MAX_SUGGESTIONS}):")
                sections.extend(lines)

    evidence = context.get("top_resume_matches")
    if isinstance(evidence, list):
        lines = _format_evidence_items(evidence)
        if lines:
            sections.append(f"Resume evidence snippets (max {MAX_EVIDENCE_ITEMS}):")
            sections.extend(lines)

    sections.extend(
        [
            "",
            f"User question: {safe_user_message}",
            "",
            "Answer now. Follow the response format and honesty rules exactly.",
        ]
    )
    return "\n".join(sections)


def call_ollama(prompt: str) -> str:
    """Call Ollama's generate API and return text or a friendly error."""
    config_error = validate_ollama_config()
    if config_error:
        return config_error

    mode = get_ollama_mode()
    base_url = _get_ollama_base_url()
    url = get_ollama_generate_url()
    model = str(getattr(settings, "ollama_model", "") or "llama3.2:1b").strip()
    timeout = _get_timeout_seconds()

    _log.info("LLM request: mode=%s model=%s url=%s timeout=%ss", mode, model, url, timeout)

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_ctx": 4096,
        },
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=get_ollama_headers(),
        method="POST",
    )

    http_status = None
    raw_body = ""
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            http_status = getattr(resp, "status", None)
            raw_body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        _log.warning("LLM HTTP error: mode=%s model=%s status=%s", mode, model, exc.code)
        combined = f"{exc.reason} {body}".lower()
        if mode == "cloud":
            if exc.code in {401, 403}:
                return "Ollama Cloud authentication failed. Check your OLLAMA_API_KEY."
            if exc.code == 404:
                return (
                    "The configured Ollama model is not available for this account or endpoint."
                )
            if exc.code == 429:
                return (
                    "Ollama Cloud rate limit reached. Try again later or switch to local mode."
                )
            return (
                f"Ollama Cloud returned an HTTP {exc.code} error. "
                "Try again later or switch to local mode."
            )
        if exc.code == 404 or ("model" in combined and "not found" in combined):
            return (
                f"Ollama model '{model}' was not found. "
                f"Run `ollama pull {model}` and try again."
            )
        return (
            f"Ollama returned an HTTP {exc.code} error. "
            "Check the local Ollama server and try again."
        )
    except (TimeoutError, socket.timeout):
        _log.warning("LLM timeout: mode=%s model=%s timeout=%ss", mode, model, timeout)
        if mode == "cloud":
            return (
                f"Ollama Cloud took longer than {timeout} seconds to respond. "
                "Try again later or switch to local mode."
            )
        return (
            f"Ollama took longer than {timeout} seconds to respond. "
            "Try again or use a smaller local model."
        )
    except urllib.error.URLError:
        _log.warning("LLM unreachable: mode=%s model=%s url=%s", mode, model, url)
        if mode == "cloud":
            return (
                f"Ollama Cloud is unreachable at {base_url}. "
                "Check your network connection or switch to local mode."
            )
        return (
            f"Ollama is not running or is unreachable at {base_url}. "
            "Start Ollama locally and try again."
        )
    except Exception as exc:
        _log.exception("LLM unexpected error: mode=%s model=%s error=%r", mode, model, exc)
        if mode == "cloud":
            return (
                "Ollama Cloud could not generate a response. "
                "Check your cloud model, API key, or account access."
            )
        return (
            "Ollama could not generate a response. "
            "Check your local Ollama setup and try again."
        )

    try:
        data = json.loads(raw_body)
    except json.JSONDecodeError:
        _log.warning(
            "LLM invalid JSON: mode=%s model=%s status=%s snippet=%.200s",
            mode, model, http_status, raw_body[:200],
        )
        if mode == "cloud":
            return (
                "Ollama Cloud returned an invalid response. "
                "Try again later or switch to local mode."
            )
        return "Ollama returned an invalid response. Check the local LLM setup and try again."

    response_text = _normalize_response_text(data.get("response"), 4000)
    _log.info(
        "LLM parsed: mode=%s model=%s status=%s keys=%s snippet=%.300s",
        mode, model, http_status, list(data.keys()),
        response_text[:300] if response_text else "",
    )
    if not response_text:
        if mode == "cloud":
            return (
                "Ollama Cloud returned an empty response. "
                "Try another cloud model or check your account access."
            )
        return "Ollama returned an empty response. Try again with a shorter question."
    return response_text


def _build_disabled_fallback(analysis_context: dict, user_message: str) -> str:
    """Return grounded, rule-based advice when the LLM feature is disabled."""
    context = _to_plain_data(analysis_context) if analysis_context else {}
    if not isinstance(context, dict):
        context = {}

    lines = [
        "Local LLM chat is disabled, so here is a rule-based answer from the current analysis.",
    ]

    score = context.get("match_score")
    if score is not None:
        lines.append(f"Match score: {_normalize_text(score, 40)}.")

    summary = _normalize_text(context.get("summary"), 300)
    if summary:
        lines.append(f"Summary: {summary}")

    missing = context.get("missing_skills")
    if isinstance(missing, list) and missing:
        names = []
        for item in missing[:3]:
            item = _to_plain_data(item)
            if isinstance(item, dict):
                name = _normalize_text(item.get("skill") or item.get("name"), 80)
            else:
                name = _normalize_text(item, 80)
            if name:
                names.append(name)
        if names:
            lines.append(
                "Top gaps to address honestly: "
                f"{', '.join(names)}. Only add them if you can support them with real experience."
            )

    suggestions = context.get("resume_suggestions") or context.get("action_steps")
    if isinstance(suggestions, list) and suggestions:
        lines.append(f"Next step: {_normalize_text(suggestions[0], 240)}")
    else:
        lines.append(
            "Next step: use the matched skills and selected evidence to make truthful, specific resume bullets."
        )

    if user_message:
        lines.append("Enable the local Ollama setting later for conversational follow-up.")
    return "\n".join(lines)


def generate_chat_response(analysis_context: dict, user_message: str) -> str:
    """Generate a local chatbot response from existing analysis context."""
    if not str(user_message or "").strip():
        return "Please enter a question about the current resume analysis."

    if not analysis_context:
        return "Run a resume analysis first, then ask a question about the results."

    if not is_llm_enabled():
        return _build_disabled_fallback(analysis_context, user_message)

    prompt = build_chat_prompt(analysis_context, user_message)
    return clean_chat_response(call_ollama(prompt))
