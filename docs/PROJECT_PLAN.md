# Project Plan

ResumeMatch AI is a local MVP resume and job description matcher. The goal is to demonstrate a complete full-stack RAG-style workflow without adding authentication, deployment, payments, or unnecessary platform features.

## MVP Goal

Build a portfolio-ready web app where a user can upload a PDF or DOCX resume, paste a job description, and receive:

- Estimated match score.
- Human-readable summary.
- Matched skills.
- Missing skills.
- Rule-based resume suggestions.
- Selected semantic resume evidence.

## Architecture

```text
Frontend HTML/CSS/JS
        |
        | multipart/form-data
        v
FastAPI /api/analyze
        |
        +-- Resume parser: PDF/DOCX text extraction
        +-- Job parser: cleaning and keyword skill extraction
        +-- Chunker: resume chunk creation
        +-- Embeddings: local sentence-transformers model
        +-- Vector store: local ChromaDB session collection
        +-- Matcher: semantic filtering and score calculation
        +-- Suggestions: rule-based action steps
        v
JSON response rendered by frontend
```

## Data Safety Scope

- Uploaded files are read from request bytes.
- Uploaded resumes are not permanently saved by the app.
- Resume chunk text and embeddings may be written to local ChromaDB during analysis.
- ChromaDB data lives under `backend/data/chroma` and is ignored by Git.
- Raw embeddings are not returned to the frontend.
- Full raw resume text is not returned to the frontend.

## Non-Goals For The MVP

- No login system.
- No deployment.
- No payment or billing.
- No user database.
- No LLM integration.
- No ML model training.
- No resume rewrite generation.

## Demo Flow

1. Start the backend on `http://127.0.0.1:8000`.
2. Start the frontend on `http://127.0.0.1:5500`.
3. Upload a fake/sample resume.
4. Paste a job description.
5. Click `Analyze match`.
6. Review the score, summary, skills, suggestions, and evidence cards.

## Future Roadmap

- Add LLM-based explanations and rewrite suggestions.
- Improve skill detection with aliases, related skills, and role-specific taxonomies.
- Add richer scoring breakdowns.
- Add deployment configuration.
- Add optional accounts and saved analysis history.
- Add optional custom model training if the project later has enough labeled examples.
