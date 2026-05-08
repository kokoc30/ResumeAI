# ResumeMatch AI

ResumeMatch AI compares your resume against a job description and tells you how well you match. It extracts resume text, splits it into chunks, generates vector embeddings, and uses ChromaDB to find the most relevant evidence. You get a match score, matched and missing skills, action steps, and an optional AI chatbot that can answer follow-up questions about your results.

## Live Demo

**[https://resumematch-ai-48re.onrender.com/](https://resumematch-ai-48re.onrender.com/)**

The app is hosted on Render's free tier — the first load after inactivity may take 20–30 seconds to wake up.

## Features

- Upload a resume (PDF or DOCX)
- Paste any job description
- Match score with reasoning
- Matched and missing skills, each tagged High / Medium / Low priority
- Action steps to improve your resume
- Semantic resume evidence pulled from relevant sections
- AI chatbot for follow-up questions (Ollama local or cloud)
- Docker and Render deployment

## Tech Stack

- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Python, FastAPI
- **Embeddings:** sentence-transformers (`all-MiniLM-L6-v2`)
- **Vector DB:** ChromaDB
- **AI Chat:** Ollama (local or cloud)
- **Deployment:** Docker, Render

## How It Works

1. Resume text is extracted from the uploaded PDF or DOCX.
2. The text is split into smaller chunks.
3. Each chunk is turned into a vector embedding using `sentence-transformers`.
4. ChromaDB searches for chunks that match the job requirements.
5. Keyword matching and semantic results combine into a score, skills list, and action steps.
6. The chatbot gets a structured summary of the analysis as context for follow-up questions.

```
Resume + Job Description
  → Text chunks
  → Embeddings (all-MiniLM-L6-v2)
  → ChromaDB search
  → Match score + skills + action steps
  → AI chatbot follow-up
```

## Run Locally

Requires Python 3.10+ and PowerShell (Windows).

```powershell
git clone https://github.com/kokoc30/ResumeAI.git
cd ResumeAI
.\setup.ps1
.\start.ps1
```

`setup.ps1` creates the virtual environment, installs dependencies, and walks you through the AI chat config.  
`start.ps1` starts the backend and frontend and opens the browser automatically.

- Frontend: `http://127.0.0.1:5500`
- Backend: `http://127.0.0.1:8000`
- API docs: `http://127.0.0.1:8000/docs`

### AI Chat (Ollama)

Install [Ollama](https://ollama.com/download) and pull the default model:

```powershell
ollama pull llama3.2:1b
```

Set `LLM_ENABLED=true` in `backend/.env`. For Ollama Cloud, set `OLLAMA_MODE=cloud` with your API key. To skip the chatbot and use only resume analysis, set `LLM_ENABLED=false`.

## Deploy on Render

The project includes a `Dockerfile` and `render.yaml`. Connect the GitHub repo on Render, set the runtime to Docker, and add these environment variables in the Render dashboard:

```
EMBEDDING_DEVICE=cpu
LLM_ENABLED=true
OLLAMA_MODE=cloud
OLLAMA_BASE_URL=https://ollama.com/api
OLLAMA_MODEL=ministral-3:3b
OLLAMA_API_KEY=<your key — set in Render dashboard only, never commit>
```

## Tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests -v
```
