# Run Locally

Use these commands from the project root in Windows PowerShell.

## Prerequisites

- Python 3.11 or newer.
- Windows PowerShell or another terminal.
- A fake/sample PDF or DOCX resume for testing.

Do not use or commit real resume files while testing this portfolio project.

## Backend Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run Backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

At startup, the backend warms up the embedding model if `EMBEDDING_WARMUP_ON_STARTUP=true`. Watch the logs for the selected embedding device.

Backend health check:

```text
http://127.0.0.1:8000/api/health
```

Expected response:

```json
{
  "status": "ok",
  "message": "Resume Job Matcher API is running"
}
```

Interactive API docs:

```text
http://127.0.0.1:8000/docs
```

Local runtime info:

```powershell
curl.exe -s http://127.0.0.1:8000/api/system
```

## Run Frontend

Open a second terminal:

```powershell
cd frontend
python -m http.server 5500
```

Open:

```text
http://127.0.0.1:5500
```

## Full-Stack Usage

1. Start the backend on `http://127.0.0.1:8000`.
2. Start the frontend on `http://127.0.0.1:5500`.
3. Open the frontend in a browser.
4. Upload a fake/sample PDF or DOCX resume.
5. Paste a job description.
6. Click `Analyze match`.
7. Review the estimated score, summary, matched skills, missing skills, suggestions, and selected resume evidence.

The frontend uses a compact results layout. Long evidence snippets, missing-skill suggestions, and action steps are shortened in the browser for readability; the score remains an estimate, not a hiring decision.

The first backend startup or first analysis request can be slower because the local embedding model may need to download or load. Later requests should be faster because the model is cached in the backend process.

## Run Tests

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pytest tests -v
```

Optional live integration script, with the backend already running:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python tests/run_integration_tests.py
```

## Manual API Test

Use `curl.exe` from PowerShell:

```powershell
curl.exe -s -X POST "http://127.0.0.1:8000/api/analyze" `
  -F "resume_file=@C:\path\to\fake_sample_resume.pdf" `
  -F "job_description=We are looking for a Python backend developer with FastAPI, SQL, Docker, and AWS experience."
```

Expected response fields:

- `match_score`
- `summary`
- `matched_skills`
- `missing_skills` (sorted by importance: High → Medium → Low, capped at 10)
- `resume_suggestions`
- `top_resume_matches`

Skill detection uses a local catalog covering programming, web/cloud tools, AI/ML, compilers, quantum computing, HPC/concurrency, hardware acceleration (CUDA/FPGA/DSP/GPU), and graph algorithms. Each missing requirement is tagged `high`, `medium`, or `low` so specialized roles surface their core gaps first.

## Troubleshooting

### Backend Is Not Running

If the frontend shows a backend-offline message, start FastAPI:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### CORS Issue

The backend allows the frontend origin from `FRONTEND_ORIGIN` in `backend/.env.example`.

For local frontend testing, use:

```text
FRONTEND_ORIGIN=http://127.0.0.1:5500
```

### First Request Is Slow

The first startup or first request may download or load the `all-MiniLM-L6-v2` embedding model. Later requests should usually be faster because the model is cached and warmed up.

### GPU/CUDA Check

Inside the backend virtual environment:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

Also confirm the NVIDIA driver sees the GPU:

```powershell
nvidia-smi
```

If CUDA is unavailable but `nvidia-smi` works, install CUDA-enabled PyTorch using the command recommended by the official PyTorch install page.

### Embedding Device Settings

Auto-detect CUDA and fallback to CPU:

```env
EMBEDDING_DEVICE=auto
```

Force CUDA:

```env
EMBEDDING_DEVICE=cuda
```

Force CPU:

```env
EMBEDDING_DEVICE=cpu
```

Other optional settings:

```env
EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2
EMBEDDING_BATCH_SIZE=32
EMBEDDING_WARMUP_ON_STARTUP=true
```

### PowerShell Form Upload Issue

Some PowerShell versions do not support `Invoke-RestMethod -Form`. Use `curl.exe` for multipart upload tests.

### Port Already In Use

If port `8000` or `5500` is busy, stop the existing process or choose a different port and update the frontend/backend origin settings as needed.

## Privacy And Safety Notes

- Uploaded resume files are processed during the request and are not permanently saved by the app.
- Local ChromaDB files may appear under `backend/data/chroma`.
- Future uploaded-file storage, if any, should stay under `backend/data/uploads`.
- `backend/data/`, `.env`, virtual environments, caches, and log files should remain ignored by Git.
- Do not commit real resumes.
- Do not commit local ChromaDB data.
- The API does not return raw embedding vectors or full raw resume text.

## Frontend UX Validation Checklist

- Desktop layout is polished and readable.
- Mobile layout stacks without horizontal scrolling.
- Valid PDF/DOCX plus job text returns real results.
- Invalid file flow shows a friendly PDF/DOCX-only error.
- Empty form flow shows friendly validation errors.
- Backend-offline flow tells the user to start FastAPI on `http://127.0.0.1:8000`.
- Match score, summary, skills, suggestions, and evidence render clearly.
- No raw embeddings are visible.
- Full raw resume text is not visible.
