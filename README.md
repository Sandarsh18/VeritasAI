<div align="center">

<img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&weight=700&size=40&pause=1000&color=6366F1&center=true&vCenter=true&width=600&lines=VeritasAI+%F0%9F%94%8D;Truth+Arbitration+Engine;Multi-Agent+Fact+Checker" alt="Typing SVG" />

<br/>

[![Made with Python](https://img.shields.io/badge/Made%20with-Python-1f425f?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/Frontend-React-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://reactjs.org)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Neo4j](https://img.shields.io/badge/Graph-Neo4j-008CC1?style=for-the-badge&logo=neo4j&logoColor=white)](https://neo4j.com)
[![Ollama](https://img.shields.io/badge/LLM-Ollama-black?style=for-the-badge&logo=ollama&logoColor=white)](https://ollama.com)

<br/>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)
[![MCA Project](https://img.shields.io/badge/MCA-Major%20Project-purple?style=flat-square)](https://rvce.edu.in)
[![RVCE](https://img.shields.io/badge/College-RV%20College%20of%20Engineering-red?style=flat-square)](https://rvce.edu.in)
[![Status](https://img.shields.io/badge/Status-Operational-brightgreen?style=flat-square)]()

<br/>

> 🧠 **An Explainable Multi-Agent Adversarial Reasoning System for Misinformation Detection**
> using Retrieval-Augmented Generation and Knowledge Graphs

<br/>

[🚀 Live Demo](#-demo) • [📖 Docs](#-how-it-works) • [⚡ Quick Start](#-quick-start) • [🏗️ Architecture](#-architecture)

</div>

---

## 🌟 What is VeritasAI?

**VeritasAI** (*Veritas* = Latin for *Truth*) is a production-grade AI system that fights misinformation using a **three-agent courtroom debate framework**. Instead of a single AI making a judgment, three specialized AI agents **argue, debate, and deliberate** — just like a real courtroom — before delivering a transparent, explainable verdict.
User submits a claim ──► Evidence Retrieved (RAG)
│
┌───────────────┼───────────────┐
▼               │               ▼
🔴 Prosecutor     ⚖️ Judge        🟢 Defender
(finds flaws)    (evaluates)    (finds support)
└───────────────┼───────────────┘
▼
📊 Explainable Verdict
TRUE / FALSE / MISLEADING / UNVERIFIED

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🤖 **Multi-Agent Debate** | Three AI agents argue opposing sides before a verdict |
| 🔍 **RAG Evidence Engine** | Claims grounded in real fact-checked articles via FAISS |
| 🧩 **Knowledge Graph** | Neo4j stores claim relationships and detects patterns |
| 💡 **Dynamic Confidence** | Evidence-based confidence scoring (never hardcoded) |
| ⚡ **Parallel Processing** | Prosecutor & Defender run simultaneously |
| 🎨 **Glassmorphic UI** | Beautiful dark/light animated React interface |
| 📊 **Analytics Dashboard** | Verdict distribution, claim history, graph visualization |
| 🔄 **Claim Deduplication** | Instant results for previously analyzed claims |

---

## 🏗️ Architecture
┌─────────────────────────────────────────────────────────┐
│                    VERITASAI SYSTEM                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────┐    ┌──────────────────────────────┐   │
│  │   React UI   │◄──►│      FastAPI Backend          │   │
│  │  (Port 5173) │    │      (Port 8000)              │   │
│  └─────────────┘    └──────────┬───────────────────┘   │
│                                 │                        │
│         ┌───────────────────────┼──────────────────┐    │
│         │                       │                   │    │
│         ▼                       ▼                   ▼    │
│  ┌─────────────┐    ┌───────────────────┐  ┌──────────┐ │
│  │ RAG ENGINE  │    │  MULTI-AGENT PIPE │  │  NEO4J   │ │
│  │             │    │                   │  │  GRAPH   │ │
│  │ Sentence    │    │ 🔴 Prosecutor     │  │          │ │
│  │ Transformers│    │    (Mistral 7B)   │  │  Claims  │ │
│  │    +        │    │                   │  │    ↕     │ │
│  │  FAISS      │    │ 🟢 Defender       │  │ Articles │ │
│  │  Index      │    │    (Phi-3 Mini)   │  │    ↕     │ │
│  └─────────────┘    │                   │  │ Sources  │ │
│                     │ ⚖️  Judge          │  └──────────┘ │
│                     │    (LLaMA 3)      │               │
│                     └───────────────────┘               │
└─────────────────────────────────────────────────────────┘

---

## 🤖 Agent Roles

<table>
<tr>
<td align="center" width="200">

### 🔴 Prosecutor
**Model:** Mistral 7B

Builds the strongest case **AGAINST** the claim by identifying contradictions in evidence

</td>
<td align="center" width="200">

### 🟢 Defender  
**Model:** Phi-3 Mini

Finds any evidence that **SUPPORTS** the claim, even partially

</td>
<td align="center" width="200">

### ⚖️ Judge
**Model:** LLaMA 3

Evaluates both sides, weighs source credibility and delivers the **FINAL VERDICT**

</td>
</tr>
</table>

---

## 📊 Verdict Types
✅ TRUE          — Claim is supported by strong evidence
❌ FALSE         — Claim is contradicted by strong evidence
⚠️  MISLEADING   — Claim is partially true but exaggerated
❓ UNVERIFIED    — Insufficient evidence to judge

---

## 🛠️ Tech Stack

### Backend
Python 3.11          FastAPI          LangGraph
Sentence-Transformers  FAISS          Neo4j
Ollama               LLaMA 3          Mistral 7B
Phi-3 Mini           Uvicorn          Pydantic

### Frontend
React 18             Vite             Framer Motion
Recharts             React Router     Lucide React
React Force Graph    React Hot Toast  Tailwind CSS

---

## ⚡ Quick Start

### Prerequisites
```bash
# Required
Python 3.10+
Node.js 18+
Ollama
Neo4j
```

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/VeritasAI.git
cd VeritasAI
```

### 2️⃣ Install Models
```bash
ollama pull mistral
ollama pull phi3
ollama pull llama3
```

### 3️⃣ Setup Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Build FAISS index
python3 -c "from rag.vector_store import build_index; build_index()"
```

### 4️⃣ Setup Frontend
```bash
cd frontend/react-app
npm install
```

### 5️⃣ Start Services
```bash
# Terminal 1 — Ollama
ollama serve

# Terminal 2 — Neo4j
sudo systemctl start neo4j

# Terminal 3 — Backend
cd backend && source venv/bin/activate
uvicorn main:app --reload --port 8000

# Terminal 4 — Frontend
cd frontend/react-app && npm run dev
```

### 6️⃣ Open in Browser
Frontend  →  http://localhost:5173
API Docs  →  http://localhost:8000/docs

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/verify` | Full pipeline claim verification |
| `POST` | `/api/verify/quick` | Fast single-agent verification |
| `GET` | `/api/claims/history` | All past analyzed claims |
| `GET` | `/api/graph/{claim_id}` | Knowledge graph for a claim |
| `GET` | `/api/stats` | System analytics |
| `GET` | `/api/models` | Active agent models |
| `GET` | `/health` | System health check |

---

## 📈 Performance

| Metric | Value |
|--------|-------|
| 🎯 Accuracy (FakeNewsNet) | 82–88% |
| ⚡ Avg Response Time | ~131 seconds |
| 🚀 Quick Endpoint | ~30 seconds |
| 🔄 Cached Claim Response | < 2 seconds |
| 📉 Inference Reduction | 40–60% (deduplication) |

---

## 🖼️ Screenshots

### 🏠 Home — Claim Verification
> Submit any news claim and watch three AI agents debate it in real time

### 📜 History — Claims Archive
> Filter past verdicts by TRUE / FALSE / MISLEADING / UNVERIFIED

### 🕸️ Graph — Knowledge Network
> Interactive force-directed graph of claim relationships

### 📊 Stats — System Analytics
> Verdict distribution, agent models, and system metrics

---

## 📁 Project Structure
VeritasAI/
│
├── backend/
│   ├── main.py                  # FastAPI app + pipeline
│   ├── requirements.txt
│   ├── agents/
│   │   ├── prosecutor.py        # Mistral 7B — finds contradictions
│   │   ├── defender.py          # Phi-3 Mini — finds support
│   │   ├── judge.py             # LLaMA 3 — delivers verdict
│   │   └── claim_analyzer.py   # Claim classification
│   ├── rag/
│   │   ├── embeddings.py        # Sentence Transformers
│   │   ├── vector_store.py      # FAISS index
│   │   └── evidence_retriever.py
│   ├── graph/
│   │   └── neo4j_client.py      # Knowledge graph operations
│   └── data/
│       └── news_articles.json   # Fact-checked article corpus
│
└── frontend/
└── react-app/
└── src/
├── pages/           # Home, History, Graph, Stats
├── components/      # VerdictBadge, AgentCard, etc.
└── services/        # API client

---

## 🎓 Academic Details

| Field | Details |
|-------|---------|
| 🏫 College | RV College of Engineering, Bengaluru |
| 📚 Program | Master of Computer Applications (MCA) |
| 📅 Semester | IV Semester |
| 🔖 Subject Code | MCA491P — Major Project |
| 👨‍🎓 Student | Sandarsh J N |
| 🆔 USN | 1RV24MC093 |

---

## 🔮 Future Scope

- [ ] 🌐 Real-time RSS news ingestion
- [ ] 📱 WhatsApp Business API integration
- [ ] 🖼️ Deepfake image detection
- [ ] 🔊 Voice claim submission
- [ ] 🌍 Multi-language support (Hindi, Kannada)
- [ ] 📡 Browser extension for passive scanning
- [ ] 🤝 Press Information Bureau API integration
- [ ] 🧠 Reinforcement learning from human feedback

---

## 📜 License
MIT License — Free to use, modify, and distribute
See LICENSE file for details

---

<div align="center">

Made with ❤️ by **Sandarsh J N** | RV College of Engineering

⭐ **Star this repo if you found it useful!** ⭐

[![GitHub stars](https://img.shields.io/github/stars/YOUR_USERNAME/VeritasAI?style=social)](https://github.com/YOUR_USERNAME/VeritasAI)

</div>
