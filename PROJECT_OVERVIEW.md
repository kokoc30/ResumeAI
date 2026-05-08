# ResumeMatch AI — Project Overview

## 1. Short Summary
ResumeMatch AI is a local-first web application that evaluates how well a user's resume aligns with a specific job description. The user uploads their resume (PDF or DOCX) and pastes a job description, and the app extracts the text to analyze the match. It returns an explainable match score, an analysis summary, lists of matched and missing skills, actionable suggestions, and selected semantic resume evidence. Additionally, an optional Ollama-powered AI chatbot allows users to ask follow-up questions using the safe, structured analysis context.

## 2. Problem It Solves
Job seekers often struggle to understand exactly how well their resume matches a specific role or why they might be screened out. Traditional tools rely on weak, keyword-only matching that misses context. ResumeMatch AI solves this by combining keyword skill extraction with RAG-style semantic evidence search and AI guidance. This helps users honestly identify missing requirements and improve their resumes with real evidence, rather than inventing experience.

## 3. Core Features
- Resume PDF/DOCX upload
- Job description input
- Explainable match score
- Analysis summary
- Matched skills identification
- Missing skills identification with prioritization
- Actionable next steps and suggestions
- Top resume evidence extraction
- RAG-style semantic evidence search
- ChromaDB vector database integration
- Floating AI chatbot assistant
- Local Ollama LLM mode
- Ollama Cloud API LLM mode
- Disabled/fallback AI mode
- Automated `setup.ps1` and `start.ps1` PowerShell scripts
- Safe structured context for chatbot (prevents exposing raw files or vectors)

## 4. Tech Stack

**Frontend:**
- HTML
- CSS
- JavaScript

**Backend:**
- Python
- FastAPI
- Pydantic
- Uvicorn

**RAG / ML:**
- `sentence-transformers`
- `all-MiniLM-L6-v2`
- ChromaDB
- CUDA/GPU optional support

**LLM:**
- Ollama local
- Ollama Cloud API
- `llama3.2:1b` (local lightweight default)
- `ministral-3:3b` (cloud option example)
- `qwen3:4b` (optional stronger local model)

**Automation:**
- PowerShell `setup.ps1`
- PowerShell `start.ps1`

**Testing:**
- `pytest` for backend
- `node --check` for frontend syntax

## 5. Architecture Overview

**System Flow:**
```text
Resume PDF/DOCX
  → text extraction
  → cleaning/chunking
  → embeddings with all-MiniLM-L6-v2
  → ChromaDB vector search
  → semantic evidence
  → score + skills + suggestions
  → optional chatbot response
```

The system extracts text from the uploaded resume and cleans the job description. The resume text is chunked into logical pieces, and `sentence-transformers` generates vector embeddings for each chunk. These embeddings are temporarily stored in ChromaDB. A vector search is then performed using the job requirements to find semantically related resume evidence. The backend uses both keyword matching and this semantic evidence to calculate a match score and generate a structured response. If the user interacts with the chatbot, it uses only this structured analysis context, not the full resume file, to generate natural language answers.

## 6. How RAG Works in This Project
RAG stands for Retrieval-Augmented Generation. Instead of relying solely on exact keyword matching, the app uses semantic search to understand the meaning behind the text.
- **Retrieval:** The app finds relevant resume chunks that match the job description using vector embeddings and vector search.
- **Augmentation:** These relevant resume chunks (the evidence) are provided to the chatbot as structured context.
- **Generation:** The chatbot uses this specific context to answer user questions intelligently.

In this project, the embedding model (`all-MiniLM-L6-v2`) handles the semantic vectorization, ChromaDB acts as the vector database for retrieval, and a separate LLM handles the natural language generation.

## 7. Models Used
The application uses a two-model design to separate semantic search from natural language generation:

**Embedding model:**
- `all-MiniLM-L6-v2`
- Used exclusively for semantic search and generating vector embeddings.
- Not used for chat generation.

**Chatbot model:**
- **Local mode:** `llama3.2:1b` is the lightweight default.
- **Cloud mode:** Model depends on Ollama Cloud availability (e.g., `ministral-3:3b`).
- **Optional stronger local model:** `qwen3:4b` can be used on machines with more resources.
- Used only for generating natural-language chat responses based on the provided context.

*(Note: ChromaDB is the vector database used to store and query the embeddings, not a standalone ML model.)*

## 8. Local vs Cloud AI Modes

**Local mode:**
- `OLLAMA_MODE=local`
- `OLLAMA_BASE_URL=http://127.0.0.1:11434`
- Runs entirely on the user's local machine.
- No API key needed.

**Cloud mode:**
- `OLLAMA_MODE=cloud`
- `OLLAMA_BASE_URL=https://ollama.com/api`
- Requires a valid `OLLAMA_API_KEY`.
- The configured model must be available in the user's Ollama Cloud account.
- The API key remains strictly on the backend and is never exposed to the frontend.

**Disabled mode:**
- `LLM_ENABLED=false`
- Resume analysis continues to work seamlessly without LLM calls.
- The chatbot uses rule-based fallback guidance instead of generating natural language.

## 9. Privacy and Safety Design
- The full raw resume file is never sent to the chatbot.
- The chatbot receives only a safe, structured analysis context.
- API keys stay securely on the backend.
- Raw embeddings are never exposed to the frontend or sent to external APIs.
- The chatbot is strictly instructed not to invent skills, experience, projects, or metrics.
- Missing skills are presented with honest suggestions, advising users to add them only if they have real, demonstrable evidence.

## 10. Project Structure
- `backend/app/main.py` — Core FastAPI routes and application entrypoint.
- `backend/app/config.py` — Environment and configuration settings.
- `backend/app/llm_client.py` — Ollama local/cloud chatbot client integration.
- `backend/app/models.py` — Pydantic request and response schemas.
- `frontend/app.js` — Frontend application logic and API interactions.
- `frontend/styles.css` — UI styling and layout.
- `frontend/index.html` — Main application page structure.
- `setup.ps1` — Automated first-time environment setup script.
- `start.ps1` — Automated script to run frontend and backend simultaneously.
- `backend/.env.example` — Safe environment configuration template.

## 11. Setup and Run

**First-time setup:**
```powershell
.\setup.ps1
```

**Start app (Automated):**
```powershell
.\start.ps1
```

**Manual backend startup:**
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Manual frontend startup:**
```powershell
cd frontend
python -m http.server 5500
```

**Open:**
```text
http://127.0.0.1:5500
```

## 12. Environment Configuration
Create a `backend/.env` file. **Do not commit this file to version control.**

**Local mode example:**
```env
LLM_ENABLED=true
LLM_PROVIDER=ollama
OLLAMA_MODE=local
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2:1b
OLLAMA_API_KEY=
LLM_TIMEOUT_SECONDS=60
EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2
EMBEDDING_DEVICE=auto
```

**Cloud mode example:**
```env
LLM_ENABLED=true
LLM_PROVIDER=ollama
OLLAMA_MODE=cloud
OLLAMA_BASE_URL=https://ollama.com/api
OLLAMA_MODEL=ministral-3:3b
OLLAMA_API_KEY=your_ollama_api_key_here
LLM_TIMEOUT_SECONDS=60
EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2
EMBEDDING_DEVICE=auto
```

**Disabled mode example:**
```env
LLM_ENABLED=false
```

## 13. Testing and Validation

**Backend tests (pytest):**
```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests -v
```

**Frontend syntax check (node):**
```powershell
cd frontend
node --check app.js
```

**Status endpoint validation:**
```powershell
curl.exe http://127.0.0.1:8000/api/chat/status
```

## 14. Main API Endpoints
- `POST /api/analyze` — Accepts a resume file and job description text; returns structured match score, summary, matched/missing skills, and semantic evidence.
- `POST /api/chat` — Accepts a follow-up user message and the existing structured analysis context; returns a natural language response from the configured LLM.
- `GET /api/chat/status` — Returns non-sensitive LLM configuration status to the frontend.

## 15. Current Strengths
- Privacy-conscious local-first design.
- True RAG-style semantic search, going beyond simple keyword matching.
- Explainable evidence links specific job requirements to actual resume text.
- Safe, constrained chatbot context prevents hallucination.
- Flexible configuration supporting local or cloud LLMs.
- Lightweight, dependency-free vanilla frontend.
- Good backend test coverage.
- Easy-to-use Windows PowerShell setup and run scripts.

## 16. Limitations
- The match score is an estimate, not an official hiring decision or guarantee.
- Resume parsing quality depends heavily on the formatting of the uploaded PDF or DOCX file.
- Cloud model availability is dependent on the user's specific Ollama account permissions.
- Smaller local models may produce less sophisticated chatbot responses.
- The app currently operates statelessly and does not save user history or export reports.

## 17. Future Feature Ideas
- Exportable PDF/HTML match report.
- Resume bullet rewrite suggestions based on semantic gaps.
- Specific ATS keyword coverage score.
- Resume version comparison.
- Saved analysis history and user accounts.
- Automated job description skill extractor.
- Targeted cover letter generator.
- Multi-resume comparison for recruiters.

## 18. Final Demo Summary
"ResumeMatch AI demonstrates a practical RAG workflow by combining resume parsing, semantic vector search, explainable matching, and optional local/cloud LLM guidance in a privacy-conscious web app."
