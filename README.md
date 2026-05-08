# ResumeMatch AI

ResumeMatch AI is a local MVP web app that compares an uploaded resume with a pasted job description. It extracts resume text, identifies skill overlap, searches resume chunks with local embeddings and ChromaDB, then shows an explainable match score, summary, suggestions, and selected resume evidence.

The project is built as a portfolio-ready full-stack RAG-style application with a plain HTML/CSS/JavaScript frontend and a FastAPI backend.

## What It Does

- Upload a PDF or DOCX resume.
- Paste a job description.
- Extract and clean resume and job text.
- Detect matched and missing skills using a richer local skill/requirement catalog (programming, web, ML, compilers, quantum computing, HPC/concurrency, hardware acceleration, graph algorithms, and more).
- Classify each missing requirement as High, Medium, or Low priority based on where it appears in the job description and how specialized it is.
- Chunk resume text into smaller evidence sections.
- Generate local embeddings with `sentence-transformers`.
- Store and query resume chunks in local ChromaDB during analysis.
- Calculate an explainable estimated match score that penalizes missing high-priority requirements.
- Render score, summary, skills, suggestions, and selected evidence in the frontend.
- Ask follow-up questions in the Resume Assistant using structured analysis context.

## Tech Stack

- Frontend: plain HTML, CSS, JavaScript
- Backend: Python FastAPI
- Resume parsing: PyMuPDF and python-docx
- Embeddings: sentence-transformers with `all-MiniLM-L6-v2`
- Vector database: local ChromaDB
- Tests: pytest

## RAG-Style Pipeline

1. User uploads a resume.
2. Backend extracts text from PDF or DOCX bytes.
3. Backend cleans and validates the job description.
4. Backend extracts simple keyword skills from both texts.
5. Resume text is split into internal chunks.
6. Local embeddings are generated for resume chunks and job-side query text.
7. Resume chunks and embeddings are stored in a per-analysis ChromaDB collection.
8. Job skills or job text query the ChromaDB collection for semantic resume evidence.
9. Backend scores, summarizes, and returns selected results to the frontend.
10. Frontend renders the analysis without exposing raw embeddings or full resume text.

## Local Setup

Use Windows PowerShell from the project root.

First-time setup:

```powershell
.\setup.ps1
```

Start the app:

```powershell
.\start.ps1
```

The startup script:

- starts the backend and frontend
- opens the browser
- keeps running in the same terminal
- stops both servers when you press `Ctrl+C`
- shows busy port PIDs and asks before stopping them

- Frontend: `http://127.0.0.1:5500`
- Backend: `http://127.0.0.1:8000`
- API docs: `http://127.0.0.1:8000/docs`
- Chat status: `http://127.0.0.1:8000/api/chat/status`

### Manual Fallback

Backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
python -m http.server 5500
```

Open:

```text
http://127.0.0.1:5500
```

### AI Chat Mode Setup

Environment file:

```text
backend\.env
```

Local Ollama mode uses a local Ollama server and does not require an API key:

```env
LLM_ENABLED=true
LLM_PROVIDER=ollama
OLLAMA_MODE=local
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2:1b
OLLAMA_API_KEY=
LLM_TIMEOUT_SECONDS=60
```

Pull the default lightweight local chatbot model:

```powershell
ollama pull llama3.2:1b
```

Ollama Cloud API mode does not require running local Ollama:

```env
LLM_ENABLED=true
LLM_PROVIDER=ollama
OLLAMA_MODE=cloud
OLLAMA_BASE_URL=https://ollama.com/api
OLLAMA_MODEL=llama3.2:1b
OLLAMA_API_KEY=your_ollama_api_key_here
LLM_TIMEOUT_SECONDS=60
```

Keep the real key only in `backend\.env`. Do not commit `backend\.env`, and do not put the key in frontend JavaScript.

To disable AI chat while keeping resume analysis working:

```env
LLM_ENABLED=false
```

For higher-quality local responses on machines with more GPU/RAM, you can switch to:

```powershell
ollama pull qwen3:4b
```

Then update `backend\.env`:

```env
OLLAMA_MODEL=qwen3:4b
```

## Run Tests

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pytest tests -v
```

## AI Chatbot Modes

ResumeMatch AI includes an optional chatbot powered by Ollama. The app still works when AI chat is disabled or unavailable; resume analysis continues to work and chat returns fallback/error guidance from the structured analysis.

Local mode:

```env
LLM_ENABLED=true
LLM_PROVIDER=ollama
OLLAMA_MODE=local
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2:1b
OLLAMA_API_KEY=
LLM_TIMEOUT_SECONDS=60
```

Cloud mode:

```env
LLM_ENABLED=true
LLM_PROVIDER=ollama
OLLAMA_MODE=cloud
OLLAMA_BASE_URL=https://ollama.com/api
OLLAMA_MODEL=llama3.2:1b
OLLAMA_API_KEY=your_ollama_api_key_here
LLM_TIMEOUT_SECONDS=60
```

Disabled mode:

```env
LLM_ENABLED=false
```

`llama3.2:1b` is the beginner-friendly default. `qwen3:4b` may produce better local answers but needs more GPU/RAM.

The chatbot uses the latest structured analysis result and selected evidence snippets. It does not send the resume file, raw embedding vectors, ChromaDB internals, or full raw resume text to `/api/chat`.

## Troubleshooting

- Cloud mode says `OLLAMA_API_KEY` is missing: add the real key to `backend\.env`; do not put it in frontend files.
- Cloud authentication failed: check that the key is valid and has access to the configured model.
- Local mode says Ollama is not reachable: start Ollama and confirm `http://127.0.0.1:11434/api/tags` is reachable.
- Model not found: run `ollama pull llama3.2:1b` for local mode, or choose a model available to your Ollama Cloud account.
- Ports busy: `start.ps1` prints the PIDs and asks before stopping existing dev servers.
- PowerShell blocks scripts: run PowerShell as your user and use `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` if your policy allows it.

## Privacy Notes

- Uploaded resume files are processed during the request and are not permanently saved by the app.
- ChromaDB stores per-request chunk text and embeddings locally under `backend/data/chroma`.
- Local data under `backend/data/` is ignored by Git.
- Do not commit real resumes, local ChromaDB files, `.env` files, or virtual environments.
- The API does not return raw embedding vectors.
- The API does not return the full raw resume text.
- Chat history stays in browser memory only and is cleared on reset or a new analysis.

## Local Performance Notes

- The first backend startup or first analysis can still be slower if the embedding model needs to download or load.
- The backend warms up the embedding model at startup by default, so later analysis requests do not reload the model.
- GPU acceleration is used when CUDA-enabled PyTorch is installed and `EMBEDDING_DEVICE` allows CUDA.
- CPU fallback remains supported.

Check GPU support inside the backend virtual environment:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

Embedding device options in `backend/.env`:

```env
EMBEDDING_DEVICE=auto
```

```env
EMBEDDING_DEVICE=cuda
```

```env
EMBEDDING_DEVICE=cpu
```

If CUDA is unavailable but the machine has an NVIDIA GPU, install CUDA-enabled PyTorch using the command recommended by the official PyTorch install page.

## Limitations

- The match score is still an estimate, not a guarantee of job fit.
- Skill extraction uses an expanded local catalog with regex-based aliases - it can identify specialized topics like compilers, quantum computing, HPC, GPU/FPGA, and graph algorithms, but it is not a complete skill taxonomy.
- Importance classification uses simple section-header heuristics ("minimum qualifications", "preferred qualifications") plus a small list of specialized high-priority skills. It is not a full ontology.
- Semantic evidence depends on the local embedding model and resume chunk quality.
- Core resume suggestions are rule-based and honest - they never tell the user to add fake or unverified experience. The optional chatbot can discuss the structured analysis but does not rewrite the resume automatically.
- Deployment is not configured yet.

## Future Improvements

- Deeper local chatbot polish, such as richer formatting and guided follow-up prompts.
- Larger skill taxonomy with aliases and seniority signals.
- More detailed scoring explainability.
- Deployment with production configuration.
- Optional user accounts and saved analysis history.
- Optional custom model training later if there is enough high-quality data.

## Deployment Status

The local MVP is complete and demo-ready. A Docker-based Render deployment is now wired up - see "Deploy on Render with Docker" below.

## Deploy on Render with Docker

The project ships with a `Dockerfile`, `.dockerignore`, and an optional `render.yaml` so a single container serves both the FastAPI API and the static frontend on the same origin. Local Ollama is **not** run inside the container - production chat uses Ollama Cloud or the disabled fallback.

### 1. Push to GitHub

`backend/.env`, `backend/.venv`, `backend/data`, and `frontend/runtime-config.js` are already gitignored. Confirm `git status` does not list them, then push the project to a GitHub repository.

### 2. Create the Render Web Service

Two paths - pick one:

**Option A - Blueprint (uses `render.yaml`):**

1. Render Dashboard -> **New** -> **Blueprint**.
2. Connect the GitHub repo.
3. Confirm the import. Render reads `render.yaml` and creates the web service.
4. Open the new service and set `OLLAMA_API_KEY` in **Environment** (it is declared with `sync: false`, so Render keeps it secret).

**Option B - Manual dashboard setup:**

1. Render Dashboard -> **New** -> **Web Service** -> connect the GitHub repo.
2. Runtime: **Docker**. Root Directory: project root. Dockerfile path: `./Dockerfile`.
3. Plan: Free (or Starter for more headroom).
4. Add the environment variables below under **Environment**:

```
EMBEDDING_DEVICE=cpu
EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2
EMBEDDING_WARMUP_ON_STARTUP=true
LLM_ENABLED=true
LLM_PROVIDER=ollama
OLLAMA_MODE=cloud
OLLAMA_BASE_URL=https://ollama.com/api
OLLAMA_MODEL=ministral-3:3b
OLLAMA_API_KEY=<paste in Render dashboard, never commit>
LLM_TIMEOUT_SECONDS=60
```

5. Click **Create Web Service**. Render will build the Dockerfile (this takes a few minutes the first time - `pip install` for sentence-transformers + CPU torch + the embedding model pre-download is the largest cost).

### 3. Verify the deployment

Once the build is live, open the Render URL and run these smoke tests:

- `GET https://<service>.onrender.com/api/health` -> `{"status":"ok",...}`.
- `GET https://<service>.onrender.com/api/chat/status` -> `llm_enabled` and `mode` match what you configured.
- Use the UI to upload a sample PDF/DOCX resume + a job description -> a score, summary, and skills appear.
- If `LLM_ENABLED=true`, send a chat message -> a real reply comes back from Ollama Cloud.
- If `LLM_ENABLED=false`, the chat widget shows the rule-based fallback message.

### 4. Caveats and limitations on free / small CPU plans

- **Cold starts:** Render free dynos sleep after inactivity. The first request after wake takes roughly 10-30 s while the embedding model loads from disk into RAM. The model is pre-baked into the image, so there is no network download at runtime.
- **Memory pressure:** sentence-transformers + CPU PyTorch + ChromaDB + FastAPI is genuinely tight on the smallest tier. If startup is killed (logs show `OOMKilled` / 502s), set `EMBEDDING_WARMUP_ON_STARTUP=false` (model loads lazily on first analyze) and/or `LLM_ENABLED=false`, lower `MAX_UPLOAD_MB`, or upgrade to a paid plan.
- **First analyze is the slowest** even when warm - PyTorch JITs some kernels on first encode.
- **Local Ollama mode does NOT work on Render.** Use `OLLAMA_MODE=cloud` with a valid `OLLAMA_API_KEY`, or disable chat with `LLM_ENABLED=false`.
- **Ephemeral filesystem:** ChromaDB writes per-request to `backend/data/chroma` and the app deletes the collection in the same request. Redeploys wipe the directory, which is fine because collections are session-scoped.
- **Never commit `backend/.env`.** All real keys belong only in the Render dashboard.

### 5. Local Docker test (optional)

You can validate the image locally before deploying:

```powershell
cd C:\resumeAI
docker build -t resumematch-ai .

# Fallback chat (no API key needed)
docker run --rm -p 8000:8000 `
  -e PORT=8000 -e LLM_ENABLED=false -e EMBEDDING_DEVICE=cpu `
  resumematch-ai
```

Then open `http://127.0.0.1:8000` - the frontend is served by FastAPI on the same port, no separate static server is needed.

To test cloud chat locally (do not paste the key into your terminal history if you can avoid it - use an environment variable):

```powershell
docker run --rm -p 8000:8000 `
  -e PORT=8000 `
  -e LLM_ENABLED=true `
  -e LLM_PROVIDER=ollama `
  -e OLLAMA_MODE=cloud `
  -e OLLAMA_BASE_URL=https://ollama.com/api `
  -e OLLAMA_MODEL=ministral-3:3b `
  -e OLLAMA_API_KEY=$env:OLLAMA_API_KEY `
  -e EMBEDDING_DEVICE=cpu `
  resumematch-ai
```
