<div align="center">

# VeritasAI 🔎🧠⚖️

### Explainable Fact-Checking Through Multi-Agent Reasoning

<p>
  <img src="https://readme-typing-svg.demolab.com?font=Orbitron&weight=700&size=22&duration=2500&pause=700&color=22C55E&center=true&vCenter=true&width=960&lines=Agentic+Claim+Verification;RAG+%2B+Multi-LLM+Fallbacks;Prosecutor+vs+Defender+Debate" alt="VeritasAI typing banner" />
</p>

<p>
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/React-19-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" />
  <img src="https://img.shields.io/badge/Vite-5-646CFF?style=for-the-badge&logo=vite&logoColor=white" />
  <img src="https://img.shields.io/badge/LangGraph-0.2.66-purple?style=for-the-badge&logo=langchain" />
  <img src="https://img.shields.io/badge/FAISS-Vector%20Ranking-7C3AED?style=for-the-badge" />
</p>

<p>
  <img src="https://img.shields.io/badge/Status-Production%20Ready-22C55E?style=flat-square" />
  <img src="https://img.shields.io/badge/Architecture-Multi--Agent-0EA5E9?style=flat-square" />
  <img src="https://img.shields.io/badge/Auth-JWT-F97316?style=flat-square" />
  <img src="https://img.shields.io/badge/Export-PDF-A855F7?style=flat-square" />
  <img src="https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-000000?style=flat-square" />
</p>

</div>

---

## 📚 Table of Contents

- [What is VeritasAI?](#what-is-veritasai)
- [Key Features](#key-features)
- [Quick Start](#quick-start)
- [System Architecture](#system-architecture)
- [How It Works](#how-it-works)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Database & Authentication](#database--authentication)
- [Development](#development)
- [Performance](#performance)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## What is VeritasAI?

VeritasAI is an **explainable claim verification platform** that analyzes misinformation through multi-agent debate and evidence-based reasoning. Instead of providing a black-box verdict, it:

1. **Retrieves evidence** from multiple web sources using a hybrid RAG pipeline
2. **Generates arguments** through competing AI agents (Prosecutor 🔨 and Defender 🛡️)
3. **Synthesizes verdicts** via a Judge agent that weighs both sides
4. **Scores disagreement** to measure claim contentiousness
5. **Exports results** as shareable links, PDFs, and historical records

Perfect for journalists, researchers, and fact-checkers who need **transparency, not just accuracy**.

---

## 🚀 Key Features

### Core Capabilities
- ✅ **Agentic Multi-Agent Verification** — LangGraph-orchestrated Prosecutor/Defender/Judge debate system
- ✅ **RAG-Powered Evidence Retrieval** — FAISS semantic ranking + multi-API fallback (SerpAPI, NewsAPI, DuckDuckGo)
- ✅ **Disagreement Scoring** — Quantifies claim contentiousness and agent consensus
- ✅ **Batch Verification** — Process up to 5 claims concurrently with `/api/verify/batch`
- ✅ **Confidence Scoring** — Normalized 0-100 confidence with reasoning
- ✅ **Source Attribution** — Evidence cards with domain credibility scores

### User Features
- ✅ **Claim History** — Persistent SQLite-backed verification history
- ✅ **Shareable Links** — Short IDs for public claim sharing via `/api/share/{short_id}`
- ✅ **PDF Export** — Professional verdict reports with evidence summaries
- ✅ **JWT Authentication** — Secure user registration and login
- ✅ **Real-Time Pipeline Visualization** — See each reasoning stage as it executes
- ✅ **Responsive UI** — Modern React 19 + Vite frontend with animations

### Reliability
- ✅ **Multi-LLM Fallback Chain** — Gemini → Groq → DeepSeek → Ollama (local fallback)
- ✅ **Semantic Caching** — Skip re-processing identical claims
- ✅ **API Resilience** — Graceful degradation when external APIs fail
- ✅ **Health Checks** — Real-time service and LLM provider status at `/api/health`

---

## ⚡ Quick Start

### One-Command Setup (with venv)

```bash
# Navigate to project root
cd fake-news-ai

# Backend: Setup and start (Terminal 1)
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# (In another terminal) Frontend: Setup and start (Terminal 2)
cd frontend/react-app
npm install
npm run dev

# (In third terminal) Optional: Start Ollama for local LLM fallback (Terminal 3)
ollama serve
```

**Result:**
- Backend running on `http://localhost:8000`
- Frontend running on `http://localhost:5173`
- Database auto-initializes at `./backend/veritas.db`

**Verify setup:**
```bash
curl http://localhost:8000/api/health
```

---

## 🏗️ System Architecture

### High-Level Request Flow

```mermaid
flowchart TD
    User["👤 User"]
    UI["🎨 React UI"]
    API["⚙️ FastAPI"]
    Cache["💾 SQLite Cache"]
    Retrieval["🌐 Evidence Retrieval"]
    LLMs["🧠 LLM Fallback Chain"]
    Graph["📊 LangGraph"]
    PDF["📄 PDF Export"]
    
    User -->|Enter Claim| UI
    UI -->|POST /api/verify| API
    API -->|Check cache| Cache
    Cache -->|Cache Hit| API
    Cache -->|Cache Miss| Retrieval
    Retrieval -->|FAISS Rank| API
    API -->|Run Pipeline| Graph
    Graph -->|Prosecutor Argument| LLMs
    Graph -->|Defender Argument| LLMs
    Graph -->|Judge Synthesis| LLMs
    LLMs -->|Verdict + Confidence| Graph
    Graph -->|Result| API
    API -->|Save History| Cache
    API -->|Generate PDF| PDF
    API -->|JSON Response| UI
    UI -->|Display Results| User
```

### Backend Flow Architecture

```
User Input (Claim)
    ↓
[FastAPI Router] /api/verify
    ↓
[Cache Check] SQLite claim_hash lookup
    ├─→ CACHE HIT → Return cached result
    └─→ CACHE MISS → Continue to:
    ↓
[Claim Analysis] → Domain classification (Politics, Health, Science, etc.)
    ↓
[Retrieval] SerpAPI + NewsAPI + DuckDuckGo
    ├─→ Get 50-100 raw results
    ├─→ Filter by relevance (embedding similarity)
    ├─→ Filter by source credibility
    └─→ Rank by FAISS + BM25 hybrid score
    ↓
[Context Building] Top 10-15 evidence sources
    ↓
[Prosecutor Agent] "What's wrong with this claim?" (Gemini → Ollama fallback)
    ↓
[Defender Agent] "What's right about this claim?" (Gemini → Ollama fallback)
    ↓
[Judge Agent] Final verdict (Gemini → Ollama fallback)
    ↓
[Disagreement Scoring] Measure prosecutor-defender disagreement
    ↓
[PDF Export Prep] Generate shareable verdict
    ↓
[Database Save] Save to claim_history, create short_id
    ↓
API Response with:
  - Verdict (TRUE/FALSE/MIXED/INSUFFICIENT_DATA)
  - Confidence (0-100)
  - Evidence cards
  - Prosecutor/Defender arguments
  - Reasoning
  - Timing info
```

### Evidence Retrieval & Ranking Pipeline

```mermaid
flowchart LR
    Claim["📝 Claim"]
    Decompose["Decompose into queries"]
    Search["🔍 Multi-API Search"]
    Filter["Filter & Prioritize"]
    FAISS["🧮 FAISS Semantic Rank"]
    Context["📚 Build Context"]
    
    Claim --> Decompose
    Decompose --> Search
    Search -->|SerpAPI| Filter
    Search -->|NewsAPI| Filter
    Search -->|DuckDuckGo| Filter
    Filter --> FAISS
    FAISS --> Context
```

### Multi-Agent Verification Workflow

```mermaid
stateDiagram-v2
    [*] --> AnalyzeClaim: Extract key entities
    AnalyzeClaim --> RetrieveEvidence: Gather supporting/opposing sources
    RetrieveEvidence --> ProsecutorAnalysis: "Challenge the claim ⚔️"
    RetrieveEvidence --> DefenderAnalysis: "Support the claim 🛡️"
    ProsecutorAnalysis --> JudgeAnalysis: Synthesize evidence
    DefenderAnalysis --> JudgeAnalysis
    JudgeAnalysis --> Score: Calculate disagreement
    Score --> Verdict: "TRUE | FALSE | MISLEADING | UNVERIFIED"
    Verdict --> Export: Generate shareable link + PDF
    Export --> [*]
```

### Frontend Component Hierarchy

```
<App />
├─ <Routes>
├─ <Home />                    # Main verification page
│  ├─ <input> Claim entry
│  ├─ <PipelineProgress />    # Shows processing stages
│  ├─ <VerdictBadge />        # Verdict display
│  ├─ <ConfidenceGauge />     # Confidence visualization
│  ├─ <AgentCard />           # Prosecutor arguments
│  ├─ <AgentCard />           # Defender arguments
│  └─ <EvidenceCard />        # Evidence sources (multiple)
├─ <History />                 # Past claims
│  └─ Replay from cache
├─ <Login /> / <Register />    # Auth pages
├─ <Profile />                 # User settings
└─ <Stats />                   # Statistics dashboard
```

---

## 🧭 How It Works

### 1. Claim Submission
User enters a claim via the React UI. The claim is tokenized into searchable sub-queries.

### 2. Cache Check
System checks SQLite cache for identical claims (hash-based):
- **Hit** → Return cached result immediately
- **Miss** → Proceed to evidence retrieval

### 3. Evidence Gathering (RAG Pipeline)
- **Query Decomposition** → Break claim into sub-questions
- **Multi-Source Retrieval** → Search SerpAPI, NewsAPI, DuckDuckGo in parallel
- **Relevance Filtering** → Remove off-topic and low-quality sources using embeddings
- **Credibility Scoring** → Rate domain reputation (100 = very trustworthy)
- **FAISS Ranking** → Semantic ranking based on embedding similarity
- **Result** → Top 10-15 high-quality evidence sources

### 4. Prosecutor Analysis (Agent 1)
The Prosecutor agent (powered by Gemini/Ollama):
- Identifies weaknesses in the claim
- Finds contradicting evidence
- Generates structured counter-arguments (3-5 points)
- Assigns strength score: `weak | medium | strong`
- Cites specific evidence sources

### 5. Defender Analysis (Agent 2)
The Defender agent (powered by Gemini/Ollama):
- Identifies strengths in the claim
- Finds supporting evidence
- Generates structured pro-arguments (3-5 points)
- Assigns strength score: `weak | medium | strong`
- Cites specific evidence sources

### 6. Judge Synthesis (Agent 3)
The Judge agent (powered by Gemini/Ollama):
- Reviews both prosecutor and defender cases
- Weighs evidence credibility
- Produces final verdict: `TRUE | FALSE | MISLEADING | UNVERIFIED | INSUFFICIENT_DATA`
- Assigns confidence: `0-100` (normalized)
- Generates structured reasoning with citations

### 7. Disagreement Scoring
- Compares Prosecutor and Defender argument strengths
- Returns `disagreement_score: 0.0-1.0`
  - `0.0` = Strong consensus (both sides agree)
  - `1.0` = Maximum disagreement
- Labels as `Low | Medium | High` contentiousness
- Tracks support/contradict counts

### 8. Result Persistence
- Save to SQLite cache (keyed by claim hash)
- Generate short ID for sharing
- Create verifiable history record
- (Optional) Store to Neo4j knowledge graph
- Generate PDF report

---

## 🛠️ Tech Stack

### Frontend

| Technology | Purpose | Version |
|---|---|---|
| **React** | Interactive component framework | 19.2.4 |
| **Vite** | Lightning-fast dev server & build | 8.0.1 |
| **React Router** | Client-side navigation | 7.13.1 |
| **Axios** | HTTP client for API calls | 1.13.6 |
| **Framer Motion** | Smooth animations & transitions | 12.38.0 |
| **Chart.js** | Analytics dashboard charts | 4.5.1 |
| **Lucide React** | Beautiful icon library | 1.0.0 |
| **Tailwind CSS** | Utility-first styling | via tailwind-merge |

### Backend

| Technology | Purpose | Version |
|---|---|---|
| **FastAPI** | High-performance async REST API | 0.111.0 |
| **Uvicorn** | ASGI server with auto-reload | 0.29.0 |
| **SQLAlchemy** | ORM for database operations | 2.0.30 |
| **SQLite** | Local persistent database | built-in |
| **LangGraph** | Agent orchestration & state management | 0.2.66 |
| **Pydantic** | Data validation & serialization | via SQLAlchemy |
| **JWT + bcrypt** | Secure authentication | python-jose, passlib |

### AI/ML & Data

| Technology | Purpose | Version |
|---|---|---|
| **LangChain** | LLM and agent utilities | compatibility layer |
| **FAISS** | Vector similarity search & ranking | 1.8.0 (CPU) |
| **Sentence-Transformers** | Semantic embeddings | 2.7.0 |
| **SerpAPI** | Google Search integration | 2.4.2 |
| **NewsAPI** | News articles retrieval | 0.2.7 |
| **DuckDuckGo Search** | Privacy-respecting web search | 8.1.1 |

### LLM Providers (Fallback Chain)

| Provider | Model | Purpose | Status |
|---|---|---|---|
| **Google Gemini** | 2.5-flash | Primary fast reasoning | ✅ Active |
| **Groq** | llama-3.3-70b | High-quality analysis | ⚠️ Legacy |
| **DeepSeek** | reasoner | Extended reasoning | ⚠️ Legacy |
| **Ollama** | llama3.2:1b | Local fallback inference | ✅ Recommended |

### Export & Utilities

| Technology | Purpose | Version |
|---|---|---|
| **ReportLab** | PDF generation | 4.5.0 |
| **Beautiful Soup 4** | HTML parsing | 4.12.3 |
| **lxml** | XML/HTML processing | 5.3.0 |
| **FeedParser** | RSS/feed parsing | 6.0.11 |
| **Neo4j** | Graph database (optional) | 5.19.0 |

---

## 📦 Installation

### Prerequisites

- **Python** 3.10 or higher
- **Node.js** 18+ and npm 9+
- **Optional:** Ollama runtime for local LLM fallback
- **Optional:** Neo4j server for knowledge graph features

### Backend Setup

#### Step 1: Create Virtual Environment
```bash
cd backend
python3 -m venv venv
```

**Why venv?**
- Isolates Python packages from system Python
- Prevents dependency conflicts with other projects
- Makes deployment reproducible
- Allows exact version pinning

#### Step 2: Activate Virtual Environment
```bash
# macOS/Linux
source venv/bin/activate

# Windows PowerShell
venv\Scripts\Activate.ps1

# Windows Command Prompt
venv\Scripts\activate.bat
```

**You'll see:** `(venv)` prefix in terminal = activated

#### Step 3: Install Dependencies
```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

**Installation time:** ~2-5 minutes depending on internet speed

#### Step 4: Verify Installation
```bash
# Check key packages
python3 -c "import fastapi, sentence_transformers, faiss; print('✓ All imports OK')"
```

#### Step 5: Start Backend
```bash
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Health check:**
```bash
curl http://localhost:8000/api/health
```

### Frontend Setup

#### Step 1: Install Dependencies
```bash
cd frontend/react-app
npm install --legacy-peer-deps
# Or for reproducible install from lock file:
npm ci
```

**Note:** `npm ci` is preferred in CI/production; `npm install` updates lock file

#### Step 2: Verify Installation
```bash
npm run lint   # Check for syntax errors
npm run build  # Test production build
```

**Build should complete in <30 seconds**

#### Step 3: Start Development Server
```bash
npm run dev -- --host 0.0.0.0 --port 5173
```

Open in browser: `http://localhost:5173`

### Optional: Ollama Setup

For local LLM fallback (recommended for development):

```bash
# Download and start Ollama from https://ollama.ai
# In a separate terminal, ensure Ollama is running:
ollama serve

# Pull a model (default is llama3.2):
ollama pull llama3.2:1b

# Verify connection:
curl http://localhost:11434/api/version
```

---

## 🔐 Configuration

### Port Configuration

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| **Backend API** | 8000 | HTTP | FastAPI endpoints |
| **Frontend Dev** | 5173 | HTTP | Vite dev server |
| **Ollama LLM** | 11434 | HTTP | Local LLM server |
| **SQLite DB** | - | File | `./veritas.db` |
| **Neo4j (optional)** | 7687 | Bolt | Graph database |

### Environment Variables

Create `backend/.env` file:

```env
# ═══════════════════════════════════════════════════════════════
# SECURITY & CORE
# ═══════════════════════════════════════════════════════════════
SECRET_KEY=change_this_for_production_use_openssl_rand_hex_32
# Used for: JWT token signing, password hashing
# Generate with: openssl rand -hex 32

CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
# For production: https://yourdomain.com

# ═══════════════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════════════
DATABASE_URL=sqlite:///./veritas.db
# Local SQLite: creates veritas.db in backend/ folder
# PostgreSQL: postgresql://user:password@localhost/veritas
# MySQL: mysql://user:password@localhost/veritas

# ═══════════════════════════════════════════════════════════════
# SEARCH APIs (ACTIVE)
# ═══════════════════════════════════════════════════════════════
NEWSAPI_KEY=your_newsapi_key_here
# https://newsapi.org - News aggregation (100 req/day free)
# Sign up: https://newsapi.org/register

SERPAPI_KEY=your_serpapi_key_here
# https://serpapi.com - Google Search results (100 req/month free)
# Sign up: https://serpapi.com

# ═══════════════════════════════════════════════════════════════
# LLM PROVIDERS - PRIMARY
# ═══════════════════════════════════════════════════════════════
GEMINI_API_KEY=your_gemini_api_key
# https://ai.google.dev - Get key from Google AI Studio
# Model: gemini-2.5-flash (fast, free tier available)

GEMINI_MODEL=gemini-2.5-flash

# ═══════════════════════════════════════════════════════════════
# LLM PROVIDERS - SECONDARY (Legacy, optional)
# ═══════════════════════════════════════════════════════════════
GROQ_API_KEY=your_groq_api_key
GROQ_DEFENDER_MODEL=llama-3.1-8b-instant
GROQ_JUDGE_MODEL=llama-3.3-70b-versatile

DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-reasoner

# ═══════════════════════════════════════════════════════════════
# LLM PROVIDERS - FALLBACK (LOCAL)
# ═══════════════════════════════════════════════════════════════
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_ANALYZER_MODEL=llama3.2:1b
OLLAMA_MODEL=mistral:latest

# ═══════════════════════════════════════════════════════════════
# OPTIONAL: Neo4j Knowledge Graph
# ═══════════════════════════════════════════════════════════════
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-neo4j-password
```

### Getting API Keys

| Service | Free Tier | Link |
|---|---|---|
| **SerpAPI** | 100 req/month | [serpapi.com](https://serpapi.com) |
| **NewsAPI** | 100 req/day | [newsapi.org](https://newsapi.org) |
| **Google Gemini** | 60 req/min | [ai.google.dev](https://ai.google.dev) |
| **Groq** | 7500 req/day | [groq.com](https://groq.com) |
| **DeepSeek** | $5 free credit | [platform.deepseek.com](https://platform.deepseek.com) |

### CORS Configuration

**Backend CORS Settings:**
```env
CORS_ORIGINS=http://localhost:5173
```

**What this means:**
- Frontend on `http://localhost:5173` can make API calls to `http://localhost:8000`
- Prevents cross-origin request blocking
- For production, update to your domain: `CORS_ORIGINS=https://yourdomain.com`

---

## 📡 API Reference

### Verification Endpoints

#### POST `/api/verify`
Verify a single claim with full multi-agent pipeline.

**Request:**
```json
{
  "claim": "The Earth orbits the Sun"
}
```

**Response:**
```json
{
  "success": true,
  "claim": "The Earth orbits the Sun",
  "verdict": "TRUE",
  "confidence": 98,
  "disagreement_score": 0.05,
  "contentiousness": "Low",
  "reasoning": "Scientific consensus confirms...",
  "prosecutor_analysis": {
    "arguments": ["..."],
    "strength": "weak"
  },
  "defender_analysis": {
    "arguments": ["..."],
    "strength": "strong"
  },
  "evidence": [
    {
      "title": "Earth's Orbit",
      "url": "https://example.com",
      "domain": "nasa.gov",
      "snippet": "...",
      "relevance_score": 0.95,
      "credibility": 98
    }
  ],
  "history_id": "12345",
  "short_id": "abc123",
  "cache_hit": false,
  "processing_time_seconds": 45.23
}
```

#### POST `/api/verify/batch`
Verify up to 5 claims concurrently.

**Request:**
```json
{
  "claims": [
    "Claim 1",
    "Claim 2",
    "Claim 3"
  ]
}
```

**Response:**
```json
{
  "results": [
    { /* verify response */ },
    { /* verify response */ },
    { /* verify response */ }
  ],
  "total_time_seconds": 120.5
}
```

#### POST `/api/verify/quick`
Quick verification wrapper around `/verify`.

---

### History & Sharing

#### GET `/api/claims/history`
Retrieve user's claim verification history.

**Response:**
```json
{
  "claims": [
    {
      "id": 1,
      "claim": "Sample claim",
      "verdict": "TRUE",
      "confidence": 85,
      "timestamp": "2026-05-11T10:30:00Z",
      "short_id": "abc123",
      "domain": "health"
    }
  ],
  "is_authenticated": true,
  "total": 42
}
```

#### GET `/api/claims/history/{history_id}`
Retrieve detailed verification snapshot.

**Response:** Full verification response (same as `/api/verify`)

#### GET|HEAD `/api/export/pdf/{history_id}`
Download PDF report for a verification.

**Example:**
```bash
curl -o verdict.pdf http://localhost:8000/api/export/pdf/12345
```

#### GET `/api/share/{short_id}`
Public view of a shared verification (no auth required).

---

### Authentication

#### POST `/api/auth/register`
Register new user.

**Request:**
```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "john@example.com",
  "created_at": "2026-05-11T10:30:00Z"
}
```

#### POST `/api/auth/login`
Login user.

**Request:**
```json
{
  "username": "johndoe",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com"
  }
}
```

#### GET `/api/auth/me`
Get current authenticated user.

#### GET `/api/auth/check-username`
Check username availability.

#### GET `/api/auth/check-email`
Check email availability.

---

### Utility Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Service health + LLM provider status |
| `/api/stats` | GET | Aggregate verification statistics |
| `/api/trending` | GET | Top trending claims being verified |
| `/api/sources` | GET | Supported evidence sources metadata |

---

## 📁 Project Structure

```
fake-news-ai/
├── README.md                          # Main documentation (this file)
├── PROJECT_SETUP_GUIDE.md            # Detailed setup reference (deprecated, merged here)
├── .github/
│   └── workflows/
│       └── secret-scan.yml           # GitHub Actions CI/CD
├── .gitleaks.toml                    # Secret scanning config
├── .pre-commit-config.yaml           # Pre-commit hooks
│
├── backend/
│   ├── main.py                       # FastAPI app + route handlers
│   ├── agents.py                     # LangGraph orchestrator
│   ├── state.py                      # VerificationState definition
│   ├── rag_core.py                   # RAG pipeline (FAISS ranking)
│   ├── retrieval.py                  # Multi-source evidence retrieval
│   ├── filters.py                    # Source quality filters
│   ├── credibility.py                # Domain credibility scoring
│   ├── database.py                   # SQLAlchemy models + ORM
│   ├── auth.py                       # JWT authentication logic
│   ├── pdf_export.py                 # ReportLab PDF generation
│   ├── llm_client.py                 # Multi-LLM fallback chain
│   ├── gemini_client.py              # Gemini-specific client
│   │
│   ├── agents/
│   │   ├── claim_analyzer.py         # Entity extraction + analysis
│   │   ├── prosecutor.py             # Prosecutor agent
│   │   ├── defender.py               # Defender agent
│   │   ├── judge.py                  # Judge agent (verdict synthesis)
│   │   └── source_tracker.py         # Evidence attribution
│   │
│   ├── rag/
│   │   ├── embeddings.py             # Sentence transformer wrappers
│   │   ├── faiss_store.py            # FAISS vector store
│   │   ├── retriever.py              # RAG retriever interface
│   │   ├── knowledge_base.py         # Knowledge base indexing
│   │   └── realtime_fetcher.py       # Real-time source fetching
│   │
│   ├── services/
│   │   ├── cache_service.py          # Semantic caching
│   │   ├── credibility_service.py    # Credibility scoring
│   │   ├── evidence_classifier.py    # Evidence categorization
│   │   ├── metrics_service.py        # Analytics/metrics
│   │   ├── ranking_service.py        # Evidence ranking utilities
│   │   └── llm_client.py             # LLM provider integration
│   │
│   ├── tests/
│   │   ├── conftest.py               # pytest configuration
│   │   ├── test_gemini.py            # Gemini integration tests
│   │   ├── test_pipeline_recovery.py # Fallback mechanism tests
│   │   ├── test_retriever_*.py       # RAG pipeline tests
│   │   └── test_search_apis.py       # Search API tests
│   │
│   ├── data/
│   │   ├── news_articles.json        # Sample dataset
│   │   └── faiss_vectors.npy         # Pre-computed embeddings
│   │
│   ├── requirements.txt              # Python dependencies (100+ packages)
│   ├── .env.example                  # Environment variable template
│   ├── start.sh                      # Backend startup script
│   └── veritas.db                    # SQLite database (auto-created)
│
└── frontend/react-app/
    ├── package.json                  # Node dependencies
    ├── vite.config.js               # Vite build configuration
    ├── eslint.config.js             # Linting rules
    │
    ├── src/
    │   ├── main.jsx                 # App entry point
    │   ├── App.jsx                  # Root component
    │   ├── App.css                  # Global styles
    │   │
    │   ├── pages/
    │   │   ├── Home.jsx             # Main verification workflow
    │   │   ├── History.jsx          # Claim history + replay
    │   │   ├── Stats.jsx            # Analytics dashboard
    │   │   ├── Login.jsx            # User login
    │   │   ├── Register.jsx         # User registration
    │   │   └── Profile.jsx          # User profile
    │   │
    │   ├── components/
    │   │   ├── AgentCard.jsx        # Prosecutor/Defender card
    │   │   ├── EvidenceCard.jsx     # Evidence item display
    │   │   ├── ConfidenceGauge.jsx  # Confidence meter
    │   │   ├── VerdictBadge.jsx     # Verdict display badge
    │   │   ├── PipelineProgress.jsx # Real-time pipeline stages
    │   │   ├── SkeletonLoader.jsx   # Loading placeholder
    │   │   ├── MetricsPanel.jsx     # Statistics panel
    │   │   └── ui/                  # Reusable UI elements
    │   │
    │   ├── hooks/
    │   │   └── useVoice.js          # Voice input/output (optional)
    │   │
    │   ├── services/
    │   │   └── api.js               # Axios API client
    │   │
    │   ├── lib/
    │   │   └── utils.ts             # Utility functions
    │   │
    │   └── assets/                  # Images, logos, icons
    │
    ├── public/                       # Static assets
    ├── start.sh                      # Frontend startup script
    └── index.html                    # HTML entry point
```

---

## 🗃️ Database & Authentication

### Database Models

#### User Table
```sql
CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  username VARCHAR(64) UNIQUE NOT NULL,
  email VARCHAR(128) UNIQUE NOT NULL,
  hashed_password VARCHAR(256) NOT NULL,
  created_at DATETIME DEFAULT NOW(),
  is_active BOOLEAN DEFAULT TRUE
);
```

#### ClaimHistory Table
```sql
CREATE TABLE claim_history (
  id INTEGER PRIMARY KEY,
  user_id INTEGER FOREIGN KEY,
  claim_text TEXT NOT NULL,
  verdict VARCHAR(32) NOT NULL,        -- TRUE/FALSE/MIXED/INSUFFICIENT_DATA
  confidence FLOAT NOT NULL,            -- 0.0-100.0
  domain VARCHAR(64) DEFAULT "general", -- Category (Politics, Health, etc.)
  timestamp DATETIME DEFAULT NOW(),
  short_id VARCHAR(16) UNIQUE,          -- For sharing
  bookmarked BOOLEAN DEFAULT FALSE,
  details_json TEXT                     -- Full response JSON
);
```

#### ClaimCache Table
```sql
CREATE TABLE claim_cache (
  claim_hash VARCHAR(64) PRIMARY KEY,  -- SHA256 hash
  result_json TEXT NOT NULL,
  timestamp DATETIME DEFAULT NOW(),
  ttl_seconds INTEGER DEFAULT 604800   -- 7 days
);
```

### Authentication Flow

1. **Registration** → Backend hashes password with bcrypt → Stores in DB
2. **Login** → Verifies password → Generates JWT token (24-hour expiration)
3. **API Requests** → Include `Authorization: Bearer <token>` header
4. **Token Verification** → JWT decoded and validated on each request
5. **Logout** → Frontend removes token from localStorage

**Token Structure (JWT):**
```
Header: {"alg": "HS256", "typ": "JWT"}
Payload: {"sub": "username", "exp": 1234567890, "iat": 1234567890}
Signature: HMACSHA256(header.payload, SECRET_KEY)
```

---

## 🚀 Development

### Running Both Services Locally

**Terminal 1 — Backend:**
```bash
cd fake-news-ai/backend
source venv/bin/activate
python3 -m uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd fake-news-ai/frontend/react-app
npm run dev -- --host 0.0.0.0 --port 5173
```

**Terminal 3 — Ollama (optional):**
```bash
ollama serve
```

### Building for Production

**Backend:**
```bash
# Create optimized build
cd backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
# With gunicorn for production:
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
```

**Frontend:**
```bash
cd frontend/react-app
npm run build   # Creates dist/ folder (~500KB minified)
npm run preview # Preview production build locally
```

### Testing

**Backend Tests:**
```bash
cd backend
pytest tests/ -v
```

**Frontend Build Check:**
```bash
cd frontend/react-app
npm run lint
npm run build
```

### Code Quality

**Pre-commit Hooks (Secret Scanning):**
```bash
# Install pre-commit
pip install pre-commit

# Setup git hooks
pre-commit install

# Run gitleaks scan
pre-commit run gitleaks --all-files
```

---

## ⚡ Performance

### Benchmarks (CPU-Only Inference, Ollama)

| Stage | Duration | Notes |
|---|---|---|
| Claim Analysis | 5-10s | Entity extraction + decomposition |
| Evidence Retrieval | 8-15s | Multi-API search + FAISS ranking |
| Prosecutor Agent | 60-90s | Argument generation |
| Defender Agent | 60-90s | Argument generation |
| Judge Agent | 90-120s | Verdict synthesis |
| **Total Pipeline** | **220-325s** | Full end-to-end processing |

**Optimization Strategies:**
- ✅ Semantic caching (skip re-processing identical claims)
- ✅ Parallel evidence retrieval across APIs
- ✅ FAISS indexing for fast semantic search
- ✅ Frontend request timeout: 600s (10 minutes)
- ✅ LLM context window limits to prevent slowdown
- ✅ Keep-alive settings on Ollama for warm model state

### Fallback Chain Behavior

If primary LLM fails:

1. **Gemini** (primary) → timeout
2. **Groq** (secondary) → timeout
3. **DeepSeek** (tertiary) → timeout
4. **Ollama** (local fallback) → use local inference
5. **Deterministic** → return structured placeholder verdict

API remains responsive even when external services degrade.

---

## 🛡️ Security & Privacy

### Authentication
- JWT-based stateless auth
- bcrypt password hashing (cost factor: 12)
- Secure token expiration (24 hours)
- HTTPS support (production deployment)

### Data Privacy
- Local SQLite storage (no cloud transmission by default)
- Optional Neo4j isolation
- CORS restrictions (configurable per domain)

### Secret Management
- `.env` files (ignored in version control)
- GitHub Actions secret scanning (gitleaks)
- Pre-commit hooks for leak prevention
- No hardcoded credentials in source code

### API Security
- Rate limiting (configurable)
- Input validation via Pydantic
- SQL injection prevention (SQLAlchemy ORM)
- CSRF protection (session-based)

---

## 🚦 Troubleshooting

### Backend Issues

**Error: `ModuleNotFoundError: No module named 'fastapi'`**
```bash
# Forgot to activate venv
source venv/bin/activate
pip install -r requirements.txt
```

**Error: `Port 8000 already in use`**
```bash
# Kill process using port
lsof -ti:8000 | xargs kill -9
# Or use different port
python3 -m uvicorn main:app --port 8001
```

**Error: `[LLM] Gemini: DISABLED` and `OLLAMA: http://localhost:11434 unreachable`**
```bash
# Check Gemini key in .env
grep GEMINI_API_KEY backend/.env

# Or start Ollama
ollama serve  # In another terminal
```

**Error: `sqlite3.OperationalError: database is locked`**
```bash
# Close any connections, then try again
# Or remove old database and restart
rm backend/veritas.db
python3 -m uvicorn main:app --port 8000 --reload
```

### Frontend Issues

**Error: `npm: command not found`**
```bash
# Install Node.js from https://nodejs.org
node --version  # Should be 16+
npm --version   # Should be 8+
```

**Error: `Cannot GET http://localhost:5173`**
```bash
# Vite dev server not running
cd frontend/react-app
npm install
npm run dev
```

**Error: `POST /api/verify 500 Internal Server Error`**
1. Check backend logs: `tail -f backend/veritas_debug.log`
2. Verify .env files are correct
3. Check API keys (Gemini, NewsAPI, SerpAPI)
4. Ensure Ollama is running if using fallback

### Frontend Cannot Connect to Backend

**Error: `ERR_CONNECTION_REFUSED` or `CORS error`**
```bash
# 1. Verify backend is running on port 8000
curl http://localhost:8000/docs

# 2. Check CORS_ORIGINS in backend/.env
cat backend/.env | grep CORS_ORIGINS
# Should be: http://localhost:5173

# 3. Check frontend .env
cat frontend/react-app/.env
# Should be: VITE_API_BASE_URL=http://localhost:8000

# 4. Check CORS middleware in backend/main.py
```

**Error: `npm install fails with peer dependency warnings`**
```bash
npm install --legacy-peer-deps
```

### API Key Issues

**NewsAPI 401 Unauthorized:**
```bash
# Check key in .env
grep NEWSAPI_KEY backend/.env

# Test key manually
curl "https://newsapi.org/v2/everything?q=covid&apiKey=YOUR_KEY"
```

**Gemini API quota exceeded:**
```bash
# Check quota at https://console.cloud.google.com
# Or switch to Ollama for local-only operation
# Edit .env: GEMINI_API_KEY=DISABLED
```

### Performance Issues

**Verification takes >10 seconds:**
1. **Check retrieval**: Is NewsAPI/SerpAPI responding?
   ```bash
   curl https://newsapi.org/v2/everything?q=test
   curl https://serpapi.com/search?q=test
   ```

2. **Check LLM provider**: Are Gemini/Ollama responsive?
   ```bash
   curl http://localhost:11434/api/generate
   ```

3. **Enable query caching**:
   ```bash
   # In backend/main.py, set:
   ENABLE_ADVANCED_CACHE = True
   ```

4. **Check database size**:
   ```bash
   ls -lh backend/veritas.db
   # If >100MB, consider archive old data
   ```

### Database Issues

**Lost data in veritas.db?**
```bash
# Backup database before deleting
cp backend/veritas.db backend/veritas.db.backup
rm backend/veritas.db
# Restart backend to recreate with fresh schema
```

---

## 🤝 Contributing

### Code of Conduct
Be respectful, inclusive, and constructive in all interactions.

### Development Workflow

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/my-feature`
3. **Commit** with clear messages: `git commit -m "Add feature X"`
4. **Run tests**: `pytest tests/` or `npm run lint`
5. **Push** to your fork
6. **Open** a Pull Request with description

### Reporting Bugs
- Use GitHub Issues
- Include: Python/Node version, environment, reproduction steps, error logs
- Attach relevant code snippets

### Suggesting Features
- Open a GitHub Discussion
- Explain use case and expected behavior
- Reference related issues

### Code Standards
- **Python**: PEP 8 (via pylint/flake8)
- **JavaScript**: ESLint with React rules
- **Commits**: Clear, descriptive messages
- **Documentation**: Docstrings and comments for complex logic

---

## 📊 Key Statistics

| Metric | Value |
|---|---|
| **Python Files** | 40+ |
| **React Components** | 15+ |
| **API Endpoints** | 11 |
| **Database Tables** | 3 |
| **Dependencies** | 100+ |
| **Test Suite** | 8+ test files |
| **Documentation** | 2000+ lines |

---

## 🙏 Acknowledgments

Built with:
- **LangGraph** for agent orchestration
- **FastAPI** for REST API
- **React + Vite** for frontend
- **FAISS** for vector search
- **LLM Providers** (Gemini, Groq, DeepSeek, Ollama)

---

## 📮 Support

- **Issues**: [GitHub Issues](../../issues)
- **Discussions**: [GitHub Discussions](../../discussions)
- **Email**: Contact via GitHub profile

---

## 📄 License

This project is provided as-is for educational and research purposes.

---

<div align="center">

**Made with ❤️ for transparent, explainable AI fact-checking**

**Last Updated:** May 11, 2026

[⬆ Back to top](#veritasai-)

</div>
