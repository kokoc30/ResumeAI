# Development Tasks

Completed MVP task list for ResumeMatch AI.

## Completed Tasks

### Task 1: Project Structure

Created the root project layout with separate `backend/`, `frontend/`, and `docs/` directories.

### Task 2: Backend Foundation

Added the FastAPI backend foundation, settings, health endpoint, and local run path.

### Task 3: API Models And Analyze Skeleton

Defined the initial analysis response models and `/api/analyze` endpoint skeleton.

### Task 4: Resume Parsing

Implemented PDF and DOCX resume text extraction from uploaded file bytes.

### Task 5: Job Parsing And Skill Extraction

Added job description cleaning, simple keyword skill extraction, matched skills, missing skills, and an initial keyword score.

### Task 6: Resume Chunking

Split extracted resume text into internal chunks for downstream retrieval.

### Task 7: Local Embeddings

Generated local embeddings with `sentence-transformers` and `all-MiniLM-L6-v2`.

### Task 8: ChromaDB Vector Store

Stored resume chunks and embeddings in local ChromaDB collections and queried them with job-side embeddings.

### Task 9: Semantic Matching And Explainable Score

Filtered weak semantic matches, removed duplicate evidence chunks, calculated an explainable score, built summaries, and added honest rule-based suggestions.

### Task 10: Frontend UI Foundation

Created the plain HTML/CSS/JavaScript frontend with a polished upload and job-description layout.

### Task 11: Frontend API Integration

Connected the frontend to `/api/analyze`, sent multipart form data, rendered real backend results, and handled API/network errors.

### Task 12: Frontend UX Polish

Improved score presentation, loading/error states, result cards, drag-and-drop, reset behavior, responsive layout, and accessibility basics.

### Task 13: Final Cleanup And Demo Readiness

Reviewed project files, cleaned documentation, updated ignore rules, removed generated local artifacts, and validated the MVP.

## Future Upgrades

- LLM-based resume feedback and rewrite suggestions.
- Broader skill taxonomy with aliases and related skills.
- More detailed scoring breakdown and confidence indicators.
- Deployment configuration.
- Optional user accounts and saved analysis history.
- Optional custom model training later if high-quality labeled data exists.
