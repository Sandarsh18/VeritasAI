# How to Run VeritasAI (Step-by-Step)

A simple checklist for starting the project from a fresh boot.
You need **2 terminals**: one for the backend, one for the frontend.

> Important: use **system `python3`** (NOT the `.venv`).
> The `.venv` folder is broken/incomplete. All dependencies are installed
> in system python3.

---

## TERMINAL 1 — Backend

### Step 1. Open a terminal

### Step 2. Start Ollama (optional)
Ollama is only a *fallback* reasoner. The app uses **Groq** (cloud) as the
primary reasoning engine, so it works even if Ollama is off. Start it only if
you want a local fallback:
```bash
ollama serve
```
If it says "address already in use", Ollama is already running — that's fine.

### Step 3. Check Ollama models (optional)
In another tab/terminal:
```bash
ollama list
```
You should see: `mistral:latest`, `llama3.2:1b`, `phi3:latest`.

### Step 4. Check Docker (only if running via Docker)
```bash
docker ps
```
For normal local dev you do NOT need Docker. Skip to Step 5.

### Step 5. Go to the backend folder
```bash
cd ~/projects/Mp/fake-news-ai/backend
```

### Step 6. Start the backend (system python3, NOT venv)
```bash
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```
Wait until you see:
```
[LLM] Groq: ready (llama-3.3-70b-versatile)
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```
Verify in a browser or curl:
- Health: http://localhost:8000/api/health
- API docs: http://localhost:8000/docs

Leave this terminal running.

---

## TERMINAL 2 — Frontend

### Step 7. Open a SECOND terminal

### Step 8. Go to the React app folder
```bash
cd ~/projects/Mp/fake-news-ai/frontend/react-app
```

### Step 9. Install dependencies (only the first time, or after a git pull)
```bash
npm install --legacy-peer-deps
```

### Step 10. Start the frontend
```bash
npm run dev
```
Wait until you see:
```
VITE v8.x ready
➜ Local: http://localhost:5173/
```

### Step 11. Open the app
Go to: **http://localhost:5173**

---

## Quick Reference (the only commands that matter)

Terminal 1 (backend):
```bash
cd ~/projects/Mp/fake-news-ai/backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Terminal 2 (frontend):
```bash
cd ~/projects/Mp/fake-news-ai/frontend/react-app
npm run dev
```

Ports:
- Backend  → http://localhost:8000  (docs at /docs, health at /api/health)
- Frontend → http://localhost:5173

---

## Troubleshooting

**"ModuleNotFoundError: No module named 'sqlalchemy'" (or uvicorn, groq, etc.)**
You accidentally used the broken venv. Use system python3 instead. If a module
is genuinely missing, reinstall:
```bash
cd ~/projects/Mp/fake-news-ai/backend
pip install -r requirements.txt --break-system-packages
```

**"Address already in use" on port 8000**
An old backend is still running. Kill it:
```bash
pkill -f "uvicorn main:app"
```
Then start again.

**Verify button shows ERR_CONNECTION_REFUSED / Network Error**
The frontend must point to port 8000. Check this file:
```bash
cat ~/projects/Mp/fake-news-ai/frontend/react-app/.env
```
It must say: `VITE_API_BASE_URL=http://localhost:8000`
After changing `.env`, restart `npm run dev`.

**Verdicts look wrong / "No prosecutor analysis"**
Make sure LLM agents are enabled in `backend/.env`:
```
VERITAS_ENABLE_LLM_AGENTS=1
GROQ_API_KEY=gsk_...   (must be a valid Groq key)
```
Restart the backend after editing `.env`.

**Frontend port shows 5174 instead of 5173**
That happens if 5173 is taken. Either use the printed port, or free 5173:
```bash
pkill -f vite
```

---

## Running with Docker (alternative — not needed for normal dev)

```bash
cd ~/projects/Mp/fake-news-ai
docker compose up --build -d     # start
docker compose ps                # check all 3 services are healthy
docker compose logs -f backend   # watch backend logs
docker compose down              # stop
```
Docker ports: frontend → http://localhost:5174, backend → http://localhost:8001
