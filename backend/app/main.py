"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager
import logging
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import llm_client
from app.config import settings
from app.job_parser import (
    classify_skill_importance,
    clean_job_description,
    extract_skills_from_text,
)
from app.chunker import chunk_resume_text
from app.embeddings import (
    embed_texts,
    get_embedding_device,
    is_cuda_available,
    warmup_embedding_model,
)
from app.matcher import build_summary, calculate_match_score, filter_top_matches
from app.models import (
    AnalyzeResponse,
    ChatRequest,
    ChatResponse,
    ChatStatusResponse,
    MatchedSkill,
    MissingSkill,
    ResumeMatch,
)
from app.resume_parser import extract_resume_text
from app.suggestions import build_resume_suggestions
from app.vector_store import (
    add_resume_chunks,
    create_session_collection,
    delete_session_collection,
    query_resume_chunks,
)

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Warm the local embedding model when the API process starts."""
    if settings.embedding_warmup_on_startup:
        try:
            logger.info(
                "Starting embedding model warmup: configured_device=%s, "
                "resolved_device=%s, cuda_available=%s.",
                settings.embedding_device,
                get_embedding_device(),
                is_cuda_available(),
            )
            warmup_embedding_model()
        except Exception:
            logger.exception(
                "Embedding model warmup failed. The API will continue to start, "
                "but /api/analyze may fail until the embedding configuration is fixed."
            )
    else:
        logger.info(
            "Embedding model warmup disabled: resolved_device=%s, cuda_available=%s.",
            get_embedding_device(),
            is_cuda_available(),
        )

    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check() -> dict[str, str]:
    """Return a basic API health check."""
    return {
        "status": "ok",
        "message": "Resume Job Matcher API is running",
    }


@app.get("/api/system")
def system_info() -> dict[str, str | bool | int]:
    """Return non-sensitive local embedding runtime information."""
    return {
        "status": "ok",
        "embedding_model": settings.embedding_model_name,
        "embedding_device": get_embedding_device(),
        "embedding_device_setting": settings.embedding_device,
        "embedding_batch_size": settings.embedding_batch_size,
        "embedding_warmup_on_startup": settings.embedding_warmup_on_startup,
        "cuda_available": is_cuda_available(),
    }


def _chat_provider() -> str:
    """Return the configured chat provider name."""
    return str(settings.llm_provider or "ollama").strip() or "ollama"


def _chat_mode() -> str:
    """Return the configured non-sensitive Ollama mode."""
    return llm_client.get_ollama_mode()


def _chat_model() -> str:
    """Return the configured chat model name."""
    return str(settings.ollama_model or "llama3.2:1b").strip() or "llama3.2:1b"


@app.get("/api/chat/status", response_model=ChatStatusResponse)
def chat_status() -> ChatStatusResponse:
    """Return non-sensitive LLM chat status."""
    return ChatStatusResponse(
        llm_enabled=llm_client.is_llm_enabled(),
        provider=_chat_provider(),
        mode=_chat_mode(),
        model=_chat_model(),
    )


@app.post("/api/chat", response_model=ChatResponse)
def chat_with_analysis(request: ChatRequest) -> ChatResponse:
    """Answer a follow-up question using an existing structured analysis result."""
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Chat message cannot be empty.")

    if not request.analysis_context:
        raise HTTPException(
            status_code=400,
            detail="Run a resume analysis first, then send its structured result context.",
        )

    answer = llm_client.generate_chat_response(request.analysis_context, message)
    return ChatResponse(
        answer=answer,
        provider=_chat_provider(),
        model=_chat_model(),
        llm_enabled=llm_client.is_llm_enabled(),
    )


ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_UPLOAD_BYTES = settings.max_upload_mb * 1024 * 1024


def _build_missing_skill_suggestion(skill: str, importance: str) -> str:
    """Build an honest, importance-aware suggestion for one missing skill."""
    base = f"Add '{skill}' only if you have real experience with it."
    if importance == "High":
        return (
            f"{base} If you do not, consider a focused project or course on "
            f"'{skill}' before targeting this role."
        )
    if importance == "Low":
        return (
            f"Mention '{skill}' if it appears naturally in your work, but it "
            f"is a lower-priority requirement for this role."
        )
    return base


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_resume(
    resume_file: UploadFile = File(...),
    job_description: str = Form(...),
) -> AnalyzeResponse:
    """Accept a resume file and job description, return analysis results.

    Uses keyword skill matching, local embeddings, ChromaDB vector search,
    and explainable scoring over resume chunks.
    """

    filename = resume_file.filename or ""
    extension = filename[filename.rfind("."):].lower() if "." in filename else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type '{extension}'. "
                "Only .pdf and .docx files are accepted."
            ),
        )

    if not job_description.strip():
        raise HTTPException(
            status_code=400,
            detail="Job description cannot be empty.",
        )

    file_bytes = await resume_file.read()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"File is too large ({len(file_bytes) / 1024 / 1024:.1f} MB). "
                f"Maximum allowed size is {settings.max_upload_mb} MB."
            ),
        )

    try:
        resume_text = extract_resume_text(file_bytes, filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        resume_chunks = chunk_resume_text(resume_text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        cleaned_job = clean_job_description(job_description)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Log safe stats only - never log full resume text
    logger.info(
        "Resume parsed: filename=%s, chars=%d, chunks=%d | Job description chars=%d",
        filename,
        len(resume_text),
        len(resume_chunks),
        len(cleaned_job),
    )

    resume_skills_list = extract_skills_from_text(resume_text)
    job_skills_list = extract_skills_from_text(cleaned_job)
    resume_skills = set(resume_skills_list)
    job_skills = set(job_skills_list)

    chunk_texts = [c.text for c in resume_chunks]
    resume_embeddings = embed_texts(chunk_texts)

    job_texts_to_embed = job_skills_list if job_skills_list else [cleaned_job]
    job_embeddings = embed_texts(job_texts_to_embed)

    session_id = uuid.uuid4().hex
    collection = None
    vector_matches: list[dict] = []
    try:
        collection = create_session_collection(session_id)
        add_resume_chunks(collection, resume_chunks, resume_embeddings)
        vector_matches = query_resume_chunks(
            collection,
            query_texts=job_texts_to_embed,
            query_embeddings=job_embeddings,
            top_k=3,
        )
    finally:
        if collection is not None:
            delete_session_collection(session_id)

    matched = sorted(resume_skills & job_skills)
    missing_set = job_skills - resume_skills
    semantic_matches = filter_top_matches(vector_matches)

    # Importance drives missing-skill ordering and the high-priority score penalty.
    importance_by_skill = {
        skill: classify_skill_importance(skill, cleaned_job)
        for skill in job_skills
    }
    high_priority_job_skills = {
        s for s, imp in importance_by_skill.items() if imp == "High"
    }
    high_priority_missing = high_priority_job_skills - resume_skills
    high_priority_matched = high_priority_job_skills & resume_skills

    match_score = calculate_match_score(
        matched_skill_count=len(matched),
        job_skill_count=len(job_skills),
        semantic_matches=semantic_matches,
        resume_chunk_count=len(resume_chunks),
        high_priority_missing_count=len(high_priority_missing),
        high_priority_job_count=len(high_priority_job_skills),
        high_priority_matched_count=len(high_priority_matched),
    )

    importance_order = {"High": 0, "Medium": 1, "Low": 2}
    missing_sorted = sorted(
        missing_set,
        key=lambda s: (
            importance_order.get(importance_by_skill.get(s, "Medium"), 1),
            s,
        ),
    )
    DISPLAY_MAX_MISSING = 10
    missing_displayed = missing_sorted[:DISPLAY_MAX_MISSING]

    matched_skills = [
        MatchedSkill(
            skill=s,
            confidence="high",
            resume_evidence=f"'{s}' found in resume (keyword match).",
        )
        for s in matched
    ]

    missing_skills = [
        MissingSkill(
            skill=s,
            importance=importance_by_skill.get(s, "Medium").lower(),
            suggestion=_build_missing_skill_suggestion(
                s, importance_by_skill.get(s, "Medium")
            ),
        )
        for s in missing_displayed
    ]

    resume_suggestions = build_resume_suggestions(
        missing_skills=missing_displayed,
        semantic_matches=semantic_matches,
        match_score=match_score,
    )

    summary = build_summary(
        match_score=match_score,
        matched_skill_count=len(matched),
        missing_skill_count=len(missing_displayed),
        semantic_match_count=len(semantic_matches),
    )

    top_resume_matches = [
        ResumeMatch(
            job_requirement=match["job_requirement"],
            resume_chunk=match["resume_chunk"],
            similarity_score=match["similarity_score"],
        )
        for match in semantic_matches
    ]

    return AnalyzeResponse(
        match_score=match_score,
        summary=summary,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        resume_suggestions=resume_suggestions,
        top_resume_matches=top_resume_matches,
    )


_FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if _FRONTEND_DIR.is_dir():
    app.mount(
        "/",
        StaticFiles(directory=_FRONTEND_DIR, html=True),
        name="frontend",
    )
