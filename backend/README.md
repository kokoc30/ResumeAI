# Backend

This directory contains the FastAPI backend for the ResumeMatch AI project. The backend accepts a resume file and job description, extracts and analyzes the text, searches resume chunks with local vector retrieval, and returns an explainable analysis response for the frontend.

## Endpoints

### `GET /api/health`

Returns a simple health check.

```json
{
  "status": "ok",
  "message": "Resume Job Matcher API is running"
}
```

### `POST /api/analyze`

Accepts `multipart/form-data`:

- `resume_file`: PDF or DOCX file.
- `job_description`: job description text.

Returns:

- `match_score`
- `summary`
- `matched_skills`
- `missing_skills`
- `resume_suggestions`
- `top_resume_matches`

The backend does not return raw embedding vectors or full raw resume text.

### `GET /api/chat/status`

Returns non-sensitive chatbot configuration:

```json
{
  "llm_enabled": true,
  "provider": "ollama",
  "mode": "local",
  "model": "llama3.2:1b"
}
```

### `POST /api/chat`

Accepts a follow-up question plus the structured analysis result already returned by `/api/analyze`.

```json
{
  "message": "Why is my score low?",
  "analysis_context": {
    "match_score": 72,
    "summary": "...",
    "matched_skills": [],
    "missing_skills": [],
    "resume_suggestions": [],
    "action_steps": [],
    "top_resume_matches": []
  }
}
```

Returns:

```json
{
  "answer": "...",
  "provider": "ollama",
  "model": "llama3.2:1b",
  "llm_enabled": true
}
```

The frontend should send only structured analysis context and selected evidence snippets. Do not send full raw resume text, raw embedding vectors, or uploaded files to this endpoint. When LLM chat is disabled, the endpoint returns a rule-based fallback answer. When enabled, it uses Ollama through `app.llm_client`.

## Pipeline Summary

1. Validate file type, file size, and job description length.
2. Extract resume text from uploaded PDF or DOCX bytes.
3. Clean the job description.
4. Extract simple keyword skills from resume and job text.
5. Split resume text into chunks.
6. Generate local embeddings with `sentence-transformers`.
7. Store chunk text and embeddings in a per-analysis local ChromaDB collection.
8. Query resume chunks using job skills or cleaned job text.
9. Filter semantic matches, calculate an estimated score, build summary and suggestions.
10. Delete the session collection when the request is complete.

## Environment Variables

See `.env.example`.

| Variable | Purpose | Default example |
|---|---|---|
| `APP_NAME` | FastAPI app name | `Resume Job Matcher API` |
| `APP_ENV` | Local environment label | `development` |
| `FRONTEND_ORIGIN` | Allowed CORS origin | `http://127.0.0.1:5500` |
| `MAX_UPLOAD_MB` | Maximum resume upload size | `5` |
| `EMBEDDING_MODEL_NAME` | Sentence-transformers model name | `all-MiniLM-L6-v2` |
| `EMBEDDING_DEVICE` | `auto`, `cuda`, or `cpu` | `auto` |
| `EMBEDDING_BATCH_SIZE` | Batch size for embedding calls | `32` |
| `EMBEDDING_WARMUP_ON_STARTUP` | Warm model when API starts | `true` |
| `LLM_ENABLED` | Enable optional Ollama LLM helpers | `true` |
| `LLM_PROVIDER` | LLM provider name | `ollama` |
| `OLLAMA_MODE` | `local` or `cloud` | `local` |
| `OLLAMA_BASE_URL` | Local or cloud Ollama API base URL | `http://127.0.0.1:11434` |
| `OLLAMA_MODEL` | Ollama model for chat responses | `llama3.2:1b` |
| `OLLAMA_API_KEY` | Cloud API key, backend-only secret | empty |
| `LLM_TIMEOUT_SECONDS` | Ollama request timeout | `60` |

## Install Requirements

From the project root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run Locally

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Run Tests

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pytest tests -v
```

## Ollama Chat Modes

The backend includes an optional chatbot API backed by Ollama. Local mode uses a local Ollama server:

```env
LLM_ENABLED=true
LLM_PROVIDER=ollama
OLLAMA_MODE=local
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2:1b
OLLAMA_API_KEY=
LLM_TIMEOUT_SECONDS=60
```

Install Ollama and pull the default lightweight local model:

```powershell
ollama pull llama3.2:1b
```

Cloud mode uses the Ollama Cloud API and does not require running local Ollama:

```env
LLM_ENABLED=true
LLM_PROVIDER=ollama
OLLAMA_MODE=cloud
OLLAMA_BASE_URL=https://ollama.com/api
OLLAMA_MODEL=llama3.2:1b
OLLAMA_API_KEY=your_ollama_api_key_here
LLM_TIMEOUT_SECONDS=60
```

Keep the real API key only in `backend\.env`. Do not commit `backend\.env`, and do not place the key in frontend JavaScript, docs, screenshots, or logs.

Disabled mode keeps resume analysis working and uses fallback/disabled chat guidance:

```env
LLM_ENABLED=false
```

`llama3.2:1b` is recommended for easier local setup and lower memory use. For higher-quality local responses on machines with more GPU/RAM, pull the optional model:

```powershell
ollama pull qwen3:4b
```

Then update `backend\.env`:

```env
OLLAMA_MODEL=qwen3:4b
```

If LLM chat is disabled or Ollama is unavailable, the app still works and `/api/chat` returns fallback/error guidance. Chat prompts are built from structured analysis results and selected evidence snippets only. They do not include raw embedding vectors, ChromaDB internals, uploaded files, or full raw resume text by default.

## Troubleshooting

- Cloud mode says `OLLAMA_API_KEY` is missing: add the real key to `backend\.env`.
- Cloud authentication failed: verify the key and model access for the configured account.
- Local mode says Ollama is not reachable: start Ollama and check `http://127.0.0.1:11434/api/tags`.
- Model not found: run `ollama pull llama3.2:1b` for local mode, or choose a model available to the cloud account.
- Ports busy: run `..\start.ps1` from the project root and review the PIDs it prints before allowing cleanup.
- PowerShell blocks scripts: use `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` if allowed by your machine policy.

## Local Data Notes

- ChromaDB may create local files under `backend/data/chroma`.
- Uploaded resumes are read from request bytes and are not permanently saved by the app.
- `backend/data/` is ignored by Git.
- The first startup or first request can be slower while the embedding model downloads or loads.
- The model is cached in the backend process and warmed up at startup by default.

## GPU And Embedding Performance

The backend uses CUDA when CUDA-enabled PyTorch is installed and `EMBEDDING_DEVICE` is `auto` or `cuda`. It falls back to CPU when CUDA is unavailable or when `EMBEDDING_DEVICE=cpu`.

Check GPU support:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

Check local runtime info while FastAPI is running:

```powershell
curl.exe -s http://127.0.0.1:8000/api/system
```

Force CPU:

```env
EMBEDDING_DEVICE=cpu
```

Auto-detect:

```env
EMBEDDING_DEVICE=auto
```

Force CUDA:

```env
EMBEDDING_DEVICE=cuda
```

If CUDA is unavailable but the machine has an NVIDIA GPU, install CUDA-enabled PyTorch using the command recommended by the official PyTorch install page.
