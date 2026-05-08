# API Contract

Backend API contract for ResumeMatch AI.

Base URL:

```text
http://127.0.0.1:8000
```

## `GET /api/health`

Health check endpoint.

### Success Response `200 OK`

```json
{
  "status": "ok",
  "message": "Resume Job Matcher API is running"
}
```

## `POST /api/analyze`

Analyze one resume against one job description.

### Request

Method:

```text
POST
```

URL:

```text
http://127.0.0.1:8000/api/analyze
```

Content type:

```text
multipart/form-data
```

Required fields:

| Field | Type | Required | Description |
|---|---|---|---|
| `resume_file` | File | Yes | Resume file uploaded as `.pdf` or `.docx` |
| `job_description` | string | Yes | Job description text, at least 50 characters |

Supported resume file types:

- `.pdf`
- `.docx`

### Backend Behavior

- Extracts text from the uploaded PDF or DOCX resume.
- Cleans and validates the job description.
- Detects skills with a richer local skill/requirement catalog covering programming, web/cloud tools, AI/ML, compilers, quantum computing, HPC/concurrency, hardware acceleration (CUDA/FPGA/DSP/GPU), and graph algorithms. Word-boundary regex and a few targeted patterns avoid false positives for ambiguous tokens (e.g. the letter "C" or "IR" inside ordinary words).
- Classifies each detected job-side skill as High, Medium, or Low importance using simple section-header heuristics ("minimum qualifications", "preferred qualifications") plus a small list of specialized high-priority skills.
- Splits resume text into internal chunks.
- Generates local embeddings for resume chunks and job-side query text.
- Stores resume chunks and embeddings in a local ChromaDB collection for the current analysis.
- Queries job skills, or the cleaned job description when no skills are detected, against resume chunks.
- Filters weak semantic matches and avoids duplicate resume chunks.
- Calculates an estimated score from detected skill overlap, semantic vector-search evidence, and a penalty when the resume is missing high-priority requirements.
- Sorts missing skills by importance (High → Medium → Low) and caps the displayed list at 10 to keep it useful and focused.
- Builds rule-based suggestions that are targeted to the role categories present in the missing skills (compiler/quantum/systems, hardware acceleration, algorithms) and never tell users to add fake or unverified skills.

### Success Response `200 OK`

```json
{
  "match_score": 68,
  "summary": "This resume looks like a partial match with an estimated score of 68/100. Detected 3 matched skill(s), 1 missing skill(s), and 4 useful semantic resume match(es). The resume has relevant overlap, but some important evidence is missing or could be clearer. This estimate is based on detected skills and semantic resume evidence, not a guarantee.",
  "matched_skills": [
    {
      "skill": "Python",
      "confidence": "high",
      "resume_evidence": "'Python' found in resume (keyword match)."
    }
  ],
  "missing_skills": [
    {
      "skill": "AWS",
      "importance": "medium",
      "suggestion": "Consider adding 'AWS' if you have real experience with it."
    }
  ],
  "resume_suggestions": [
    "Add AWS only if you have real experience with it.",
    "Add measurable results to the most relevant bullets so the resume evidence is easier to match to the job description."
  ],
  "top_resume_matches": [
    {
      "job_requirement": "Python",
      "resume_chunk": "Skills: Python, FastAPI, Docker, PostgreSQL",
      "similarity_score": 0.82
    }
  ]
}
```

### Response Schema

| Field | Type | Description |
|---|---|---|
| `match_score` | integer | Estimated score from 0 to 100 |
| `summary` | string | User-friendly explanation of the estimate |
| `matched_skills` | array | Skills detected in both resume and job description |
| `missing_skills` | array | Skills detected in the job description but not in the resume |
| `resume_suggestions` | array | Rule-based resume improvement suggestions |
| `top_resume_matches` | array | Filtered semantic evidence chunks from vector search |

Matched skill item:

| Field | Type |
|---|---|
| `skill` | string |
| `confidence` | string |
| `resume_evidence` | string |

Missing skill item:

| Field | Type | Notes |
|---|---|---|
| `skill` | string | Canonical skill name from the local catalog |
| `importance` | string | One of `high`, `medium`, `low` (sorted descending in the response) |
| `suggestion` | string | Honest, importance-aware advice — never asks the user to fake experience |

Top resume match item:

| Field | Type |
|---|---|
| `job_requirement` | string |
| `resume_chunk` | string |
| `similarity_score` | number |

### Error Responses

Errors use FastAPI's standard JSON shape:

```json
{
  "detail": "Error message"
}
```

Common `400 Bad Request` examples:

| Condition | Example detail |
|---|---|
| Unsupported file type | `Unsupported file type '.txt'. Only .pdf and .docx files are accepted.` |
| File too large | `File is too large (6.2 MB). Maximum allowed size is 5 MB.` |
| Empty job description | `Job description cannot be empty.` |
| Job description too short | `Job description is too short (25 chars). Please provide at least 50 characters.` |
| Unreadable resume | `Could not extract any text from the PDF file.` |

### Privacy Contract

- Raw embedding vectors are never returned.
- Full raw resume text is not returned.
- Uploaded resume files are not permanently saved by the app.
- Local ChromaDB data is stored under `backend/data/chroma` and should remain ignored by Git.
- `match_score` is an estimate, not a guarantee of job fit or hiring outcome.

## `GET /api/system`

Non-sensitive local runtime information for debugging embedding device selection.

### Success Response `200 OK`

```json
{
  "status": "ok",
  "embedding_model": "all-MiniLM-L6-v2",
  "embedding_device": "cuda",
  "embedding_device_setting": "auto",
  "embedding_batch_size": 32,
  "embedding_warmup_on_startup": true,
  "cuda_available": true
}
```

This endpoint does not expose resume text, chunk text, embeddings, or user data.
