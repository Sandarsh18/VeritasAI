<div align="center">

<img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&weight=700&size=42&pause=1000&color=6366F1&center=true&vCenter=true&width=700&lines=VeritasAI+%F0%9F%94%8D;Multi-Agent+Truth+Engine;Fake+News+%E2%9D%8C+%E2%86%92+Facts+%E2%9C%85" alt="VeritasAI" />

<br/><br/>

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://reactjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Neo4j](https://img.shields.io/badge/Neo4j-008CC1?style=for-the-badge&logo=neo4j&logoColor=white)](https://neo4j.com)
[![Ollama](https://img.shields.io/badge/Ollama-LLM-black?style=for-the-badge)](https://ollama.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

<br/>

[![Stars](https://img.shields.io/github/stars/Sandarsh18/VeritasAI?style=social)](https://github.com/Sandarsh18/VeritasAI)
[![Forks](https://img.shields.io/github/forks/Sandarsh18/VeritasAI?style=social)](https://github.com/Sandarsh18/VeritasAI)
[![Issues](https://img.shields.io/github/issues/Sandarsh18/VeritasAI?style=flat-square)](https://github.com/Sandarsh18/VeritasAI/issues)
[![MCA Project](https://img.shields.io/badge/MCA-Major%20Project-purple?style=flat-square)](https://rvce.edu.in)
[![RVCE](https://img.shields.io/badge/RVCE-Bengaluru-red?style=flat-square)](https://rvce.edu.in)
[![Status](https://img.shields.io/badge/Status-✅%20Operational-brightgreen?style=flat-square)]()

<br/>

> 🧠 **An Explainable Multi-Agent Adversarial Reasoning System**
> for Automated Misinformation Detection using
> **Retrieval-Augmented Generation** and **Knowledge Graphs**

<br/>

[🚀 Quick Start](#-quick-start) •
[🏗️ Architecture](#-system-architecture) •
[🤖 Agents](#-agent-roles) •
[📊 Performance](#-performance) •
[🎓 Academic](#-academic-details)

</div>

---

## 🌟 What is VeritasAI?

**VeritasAI** *(Veritas = Latin for Truth)* is a 
production-grade AI platform that fights misinformation 
using a **three-agent courtroom debate framework**.

Instead of one AI making a black-box judgment, three 
specialized agents **argue, cross-examine, and deliberate** — 
just like a real courtroom — before delivering a 
transparent, source-cited, explainable verdict.

> 💡 India processes **500M+ WhatsApp messages daily**.
> A significant portion carry misinformation that causes
> real harm — VeritasAI is built to fight this at scale.

---

## 🔄 How It Works
```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#E8F0FF', 'primaryTextColor': '#111827', 'primaryBorderColor': '#2563EB', 'lineColor': '#334155', 'secondaryColor': '#ECFDF5', 'tertiaryColor': '#FEF3C7', 'fontFamily': 'Arial' }}}%%
flowchart TD
    A([User submits a claim]) --> B[Claim Analyzer]
    B --> C[(Hybrid Evidence Engine)]
    C --> D[Top 3 to 5 relevant articles]
    D --> E{⚡ Parallel Execution}
    E --> F[Prosecutor Agent\nFinds contradictions]
    E --> G[Defender Agent\nFinds support]
    F --> H[Judge Agent\nEvaluates both sides]
    G --> H
    H --> I{Dynamic Confidence\nScoring}
    I --> J[(Neo4j Knowledge Graph\nStore and Deduplicate)]
    I --> K([Explainable Verdict\nTRUE / FALSE /\nMISLEADING / UNVERIFIED])
    
    style A fill:#DBEAFE,color:#111827,stroke:#2563EB
    style K fill:#DCFCE7,color:#111827,stroke:#16A34A
    style H fill:#FEF3C7,color:#111827,stroke:#D97706
    style F fill:#FEE2E2,color:#111827,stroke:#DC2626
    style G fill:#DCFCE7,color:#111827,stroke:#16A34A
    style C fill:#E0F2FE,color:#111827,stroke:#0284C7
    style J fill:#F3E8FF,color:#111827,stroke:#7C3AED
```

---

## 🏗️ System Architecture
```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#F8FAFC', 'primaryTextColor': '#111827', 'primaryBorderColor': '#334155', 'lineColor': '#475569', 'clusterBkg': '#F8FAFC', 'clusterBorder': '#94A3B8', 'fontFamily': 'Arial' }}}%%
graph TB
    subgraph UI["Frontend: React 18 + Vite (5173)"]
        P1[Home\nClaim Input]
        P2[History\nClaims Archive]
        P3[Graph\nKnowledge Network]
        P4[Stats and Sources\nUI Pages]
    end

    subgraph API["Backend: FastAPI (8000)"]
        E1[POST /api/verify]
        E2[GET /api/sources]
        E3[GET /api/history and stats]
        E4[GET /health]
    end

    subgraph RAG["Evidence Layer"]
        R1[Sentence Transformers\nall-MiniLM-L6-v2]
        R2[FAISS Archive Index]
        R3[Real-time Fetcher\nNewsAPI + GDELT + RSS]
    end

    subgraph AGENTS["Multi-Agent Pipeline"]
        AG1[Prosecutor]
        AG2[Defender]
        AG3[Judge]
    end

    subgraph MEMORY["Memory Layer"]
        N1[(Neo4j Knowledge Graph)]
        N2[(SQLite Claim Store)]
    end

    subgraph LLM["Ollama Local Models (11434)"]
        L1[llama3.2:1b]
        L2[mistral]
        L3[phi3]
    end

    UI <--> API
    API --> RAG
    RAG --> AGENTS
    AG1 --> AG3
    AG2 --> AG3
    AG3 --> MEMORY
    AGENTS <--> LLM

    style UI fill:#E0F2FE,color:#111827,stroke:#0284C7
    style API fill:#DCFCE7,color:#111827,stroke:#16A34A
    style RAG fill:#DBEAFE,color:#111827,stroke:#2563EB
    style AGENTS fill:#F3E8FF,color:#111827,stroke:#7C3AED
    style MEMORY fill:#FEF3C7,color:#111827,stroke:#D97706
    style LLM fill:#F1F5F9,color:#111827,stroke:#475569
```

---

## 🤖 Agent Roles
```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryTextColor': '#111827', 'lineColor': '#475569', 'signalColor': '#2563EB', 'signalTextColor': '#111827', 'actorBorder': '#2563EB', 'actorBkg': '#DBEAFE', 'actorTextColor': '#111827', 'labelBoxBkgColor': '#F8FAFC', 'labelBoxBorderColor': '#94A3B8', 'fontFamily': 'Arial' }}}%%
sequenceDiagram
    actor User
    participant CA as Claim Analyzer
    participant RAG as Evidence Engine
    participant P as Prosecutor
    participant D as Defender
    participant J as Judge
    participant KG as Knowledge Graph

    User->>CA: Submit claim
    CA->>CA: Classify type & extract entities
    CA->>RAG: Retrieve evidence
    RAG-->>CA: Top 5 relevant articles

    par Parallel Execution
        CA->>P: Claim + Evidence
        P-->>J: Contradictions found
    and
        CA->>D: Claim + Evidence
        D-->>J: Support found
    end

    J->>J: Weigh arguments\nand credibility scores
    J->>KG: Store claim & relationships
    J-->>User: Verdict + Confidence\nReasoning + Evidence
```

---

## ⚖️ Verdict Decision Logic
```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#F8FAFC', 'primaryTextColor': '#111827', 'primaryBorderColor': '#475569', 'lineColor': '#475569', 'fontFamily': 'Arial' }}}%%
flowchart LR
    A[Evidence\nRetrieved] --> B{Source\nCredibility}
    B -->|avg > 0.7| C{Argument\nBalance}
    B -->|avg < 0.5| D[UNVERIFIED\n30-44%]
    
    C -->|Prosecutor\nstronger| E[FALSE\n75-95%]
    C -->|Defender\nstronger| F[TRUE\n75-95%]
    C -->|Mixed\nevidence| G{Ratio}
    
    G -->|65-84%| H[MISLEADING\n55-74%]
    G -->|< 65%| I[UNVERIFIED\n45-54%]

    style E fill:#FEE2E2,color:#111827,stroke:#DC2626
    style F fill:#DCFCE7,color:#111827,stroke:#16A34A
    style H fill:#FEF3C7,color:#111827,stroke:#D97706
    style D fill:#E2E8F0,color:#111827,stroke:#64748B
    style I fill:#E2E8F0,color:#111827,stroke:#64748B
```

---

## 🕸️ Knowledge Graph Schema
```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#F8FAFC', 'primaryTextColor': '#111827', 'primaryBorderColor': '#475569', 'lineColor': '#475569', 'tertiaryColor': '#F8FAFC', 'fontFamily': 'Arial' }}}%%
erDiagram
    CLAIM {
        string id PK
        string text
        string verdict
        int confidence
        datetime analyzed_at
    }
    ARTICLE {
        string id PK
        string title
        string source
        float credibility_score
        string category
        string content
    }
    SOURCE {
        string name PK
        float trust_score
        string category
    }

    CLAIM ||--o{ ARTICLE : "CONTRADICTED_BY"
    CLAIM ||--o{ ARTICLE : "SUPPORTED_BY"
    CLAIM ||--o{ CLAIM : "RELATED_TO"
    ARTICLE }o--|| SOURCE : "PUBLISHED_BY"
```

---

## ✨ Features

| Feature | Description | Status |
|---------|-------------|--------|
| 🤖 **Multi-Agent Debate** | 3 AI agents argue opposing sides | ✅ Live |
| 🔍 **Hybrid RAG Evidence Engine** | Combines FAISS archive + real-time internet news | ✅ Live |
| 🌐 **Real-Time News Fetching** | NewsAPI + GDELT + trusted RSS feeds | ✅ Live |
| 🧾 **Full Source Attribution** | Publisher, author, date, URL, logo, source type per evidence | ✅ Live |
| 🏛️ **Trusted Source Registry** | Curated credibility registry with `/api/sources` + UI page | ✅ Live |
| 🧩 **Knowledge Graph** | Neo4j claim relationship memory | ✅ Live |
| 💡 **Dynamic Confidence** | Evidence-based scoring, never hardcoded | ✅ Live |
| ⚡ **Parallel Processing** | Prosecutor & Defender run simultaneously | ✅ Live |
| 🎨 **Glassmorphic UI** | Dark/light animated React interface | ✅ Live |
| 📊 **Analytics Dashboard** | Verdict distribution & graph viewer | ✅ Live |
| 🔄 **Claim Deduplication** | Instant results for repeated claims | ✅ Live |
| 🚀 **Quick Endpoint** | 30-second fast verification mode | ✅ Live |

---

## 🛠️ Tech Stack
```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryTextColor': '#111827', 'primaryColor': '#F8FAFC', 'lineColor': '#475569', 'fontFamily': 'Arial' }}}%%
mindmap
  root((VeritasAI))
    Backend
      Python 3.11
      FastAPI
      LangGraph
      Uvicorn
      Pydantic
    AI & ML
      LLaMA 3 Judge
      Mistral 7B Prosecutor
      Phi-3 Mini Defender
      Sentence Transformers
      FAISS Vector Search
    Database
      Neo4j Knowledge Graph
      JSON Article Corpus
    Frontend
      React 18
      Vite
      Framer Motion
      Recharts
      React Force Graph
      React Router
    Infrastructure
      Ollama Local LLM
      REST API
      CORS Middleware
```

---

## ⚡ Quick Start

### Prerequisites
```bash
Python 3.10+  |  Node.js 18+  |  Ollama  |  Neo4j
```

### 1️⃣ Clone
```bash
git clone https://github.com/Sandarsh18/VeritasAI.git
cd VeritasAI
```

### 2️⃣ Pull Models
```bash
ollama pull mistral
ollama pull phi3
ollama pull llama3
```

### 3️⃣ Backend Setup
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python3 -c "from rag.vector_store import build_index; build_index()"
```

### 4️⃣ Frontend Setup
```bash
cd frontend/react-app && npm install
```

### 5️⃣ Start Everything
```bash
# Terminal 1
ollama serve

# Terminal 2
sudo systemctl start neo4j

# Terminal 3
cd backend && source venv/bin/activate
uvicorn main:app --reload --port 8000

# Terminal 4
cd frontend/react-app && npm run dev
```

### 6️⃣ Open Browser
🌐 App    →  http://localhost:5173
📖 API    →  http://localhost:8000/docs
💚 Health →  http://localhost:8000/health

---

## 🔌 API Reference
```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#F8FAFC', 'primaryTextColor': '#111827', 'primaryBorderColor': '#475569', 'lineColor': '#475569', 'clusterBkg': '#F8FAFC', 'clusterBorder': '#94A3B8', 'fontFamily': 'Arial' }}}%%
graph LR
    subgraph Endpoints["📡 REST API — Port 8000"]
        A[POST /api/verify\nFull pipeline 131s]
        B[POST /api/verify/quick\nFast mode 30s]
        C[GET /api/claims/history\nAll past claims]
        D[GET /api/graph/id\nKnowledge graph]
        E[GET /api/stats\nAnalytics]
        F[GET /api/models\nAgent models]
        G[GET /api/sources\nSource credibility registry]
        H[GET /health\nSystem status]
    end

    style A fill:#DBEAFE,color:#111827,stroke:#2563EB
    style B fill:#DCFCE7,color:#111827,stroke:#16A34A
    style C fill:#E0F2FE,color:#111827,stroke:#0284C7
    style D fill:#F3E8FF,color:#111827,stroke:#7C3AED
    style E fill:#FEF3C7,color:#111827,stroke:#D97706
    style F fill:#FCE7F3,color:#111827,stroke:#DB2777
    style G fill:#CCFBF1,color:#111827,stroke:#0F766E
    style H fill:#E0F2FE,color:#111827,stroke:#0284C7
```

### New Evidence Response Shape (`POST /api/verify`)
- `evidence[]` now includes: `source`, `source_url`, `author`, `published_date`, `source_logo`, `source_type`, `relevance_score`, `combined_score`, `is_realtime`, `evidence_source`, `image_url`
- `evidence_summary` includes: `total`, `realtime`, `archive`, `sources_used`, `avg_credibility`, `freshest_date`

---

## 📊 Performance

| Metric | Value |
|--------|-------|
| 🎯 Accuracy (FakeNewsNet) | **82 — 88%** |
| ⚡ Full Pipeline | **~131 seconds** |
| 🚀 Quick Endpoint | **~30 seconds** |
| 🔄 Cached Claim | **< 2 seconds** |
| 📉 Inference Reduction | **40 — 60%** via deduplication |
| 🎲 Confidence Range | **30 — 97%** dynamic |
| 📰 Articles in Corpus | **30+ fact-checked (archive)** |
| 🌐 Live Evidence Sources | **NewsAPI + GDELT + RSS** |

---

## 📁 Project Structure
```text
VeritasAI/
│
├── 🐍 backend/
│   ├── main.py                    # FastAPI app + pipeline orchestration
│   ├── requirements.txt           # Python dependencies
│   │
│   ├── 🤖 agents/
│   │   ├── prosecutor.py          # 🔴 Mistral 7B — finds contradictions
│   │   ├── defender.py            # 🟢 Phi-3 Mini — finds support
│   │   ├── judge.py               # ⚖️  LLaMA 3 — delivers verdict
│   │   └── claim_analyzer.py      # 🔍 Claim classification
│   │
│   ├── 🔍 rag/
│   │   ├── embeddings.py          # Sentence Transformers
│   │   ├── vector_store.py        # FAISS index build & search
│   │   ├── realtime_fetcher.py    # Real-time news fetch + source credibility
│   │   └── evidence_retriever.py  # Hybrid local + real-time retrieval
│   │
│   ├── 🕸️  graph/
│   │   └── neo4j_client.py        # Knowledge graph operations
│   │
│   └── 📰 data/
│       └── news_articles.json     # Fact-checked article corpus
│
└── ⚛️ frontend/
    └── react-app/
        └── src/
            ├── 📄 pages/
            │   ├── Home.jsx        # Claim submission + verdict
            │   ├── History.jsx     # Claims archive with filters
            │   ├── Graph.jsx       # Knowledge graph viewer
            │   ├── Stats.jsx       # Analytics dashboard
            │   └── Sources.jsx     # Trusted source registry page
            │
            ├── 🧩 components/
            │   ├── VerdictBadge.jsx
            │   ├── ConfidenceMeter.jsx
            │   ├── PipelineVisualizer.jsx
            │   ├── AgentCard.jsx
            │   ├── EvidenceCard.jsx
            │   └── ThemeToggle.jsx
            │
            └── 🔌 services/
                └── api.js          # Axios API client
```

---

## 🖼️ Screenshots

### 🏠 Claim Verification
> Submit any news claim — watch the pipeline animate in real time

### 📜 Claims History
> Filter by TRUE / FALSE / MISLEADING / UNVERIFIED with Export CSV

### 🕸️ Knowledge Graph
> Interactive force-directed network of claim relationships

### 📊 System Stats
> Verdict distribution chart, agent models, graph node count

---

## 🎓 Academic Details

| Field | Details |
|-------|---------|
| 🏫 College | RV College of Engineering, Bengaluru |
| 📚 Program | Master of Computer Applications (MCA) |
| 📅 Semester | IV Semester — 2025-26 |
| 🔖 Subject Code | MCA491P — Major Project |
| 🌐 Domain | AI / NLP / Misinformation Detection |
| 🗺️ SDG Mapping | SDG 16 — Peace, Justice & Strong Institutions |
| 👨‍🎓 Student | Sandarsh J N |
| 🆔 USN | 1RV24MC093 |

---

## 🔮 Future Scope

- [x] 🌐 Real-time RSS + API news ingestion
- [ ] 📱 WhatsApp Business API integration
- [ ] 🖼️ Deepfake image & video detection
- [ ] 🎙️ Voice claim submission
- [ ] 🌍 Hindi & Kannada language support
- [ ] 🔌 Browser extension for passive scanning
- [ ] 📡 Press Information Bureau API integration
- [ ] 🧠 Reinforcement learning from human feedback
- [ ] 📰 Source credibility auto-scoring
- [ ] 🏆 Social media misinformation tracking

---

## 📜 License
MIT License — Free to use, modify, and distribute
Copyright (c) 2026 Sandarsh J N
See LICENSE file for complete details

---

<div align="center">

### 🙏 Acknowledgements

Special thanks to **RV College of Engineering** and the
**Department of MCA** for supporting this research project.

---

Made with ❤️ and ☕ by **Sandarsh J N**

*RV College of Engineering, Bengaluru — MCA 2024-26*

---

⭐ **If this project helped you, please give it a star!** ⭐

[![GitHub stars](https://img.shields.io/github/stars/Sandarsh18/VeritasAI?style=for-the-badge&logo=github&color=6366f1)](https://github.com/Sandarsh18/VeritasAI/stargazers)

</div>
