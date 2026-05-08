"""Data models for resumes and jobs."""

from pydantic import BaseModel, Field


class MatchedSkill(BaseModel):
    """A skill found in the resume that matches the job description."""

    skill: str
    confidence: str
    resume_evidence: str


class MissingSkill(BaseModel):
    """A skill required by the job but not found in the resume."""

    skill: str
    importance: str
    suggestion: str


class ResumeMatch(BaseModel):
    """A single resume-to-job-requirement match with a similarity score."""

    job_requirement: str
    resume_chunk: str
    similarity_score: float


class AnalyzeResponse(BaseModel):
    """Full response returned by the /api/analyze endpoint."""

    match_score: int
    summary: str
    matched_skills: list[MatchedSkill]
    missing_skills: list[MissingSkill]
    resume_suggestions: list[str]
    top_resume_matches: list[ResumeMatch]


class ChatRequest(BaseModel):
    """Request body for follow-up chat over an existing analysis result."""

    message: str
    analysis_context: dict = Field(default_factory=dict)


class ChatResponse(BaseModel):
    """Response returned by the optional local analysis chat endpoint."""

    answer: str
    provider: str
    model: str
    llm_enabled: bool


class ChatStatusResponse(BaseModel):
    """Non-sensitive status for the optional Ollama LLM chat feature."""

    llm_enabled: bool
    provider: str
    mode: str
    model: str
