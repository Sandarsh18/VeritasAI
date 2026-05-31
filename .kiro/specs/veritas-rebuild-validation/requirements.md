# Requirements Document

VeritasAI Reset, Rebuild, Fix & Validate

## Introduction

VeritasAI is an explainable, multi-agent fact-checking platform (React + Vite frontend, FastAPI + LangGraph backend, RAG evidence retrieval, multi-LLM reasoning chain, SQLite persistence, optional Neo4j, PDF export, JWT auth). Recent Docker and Tavily changes left the system in an inconsistent state that must be reset, audited, repaired, and validated end to end.

A Phase 1 code audit established the **actual** (not documented) state of the repository. The most important findings that shape these requirements:

- **Tavily is not integrated in code.** `TAVILY_API_KEY` exists in `backend/.env`, but no module, package, or call references Tavily anywhere. It must be built, not merely audited.
- **Advanced RAG is disabled by default.** `rag/retriever.py` branches on `VERITAS_USE_ADVANCED_RAG` (default `"0"`); the active path is `retrieve_evidence_minimal`, not the documented FAISS hybrid pipeline. The real `backend/.env` does not set this flag.
- **Two parallel retrieval stacks exist** (`legacy/retrieval.py` re-exported by `retrieval.py`, used by `main.py`; and `rag/retriever.py`, used by `agents.py`).
- **Docker env is degraded:** `.env.docker` has `GEMINI_API_KEY=DISABLED` and no `TAVILY_API_KEY`.
- **Secrets are committed** in `backend/.env` and `.env.docker` (Groq, Gemini, SerpAPI, NewsAPI, Tavily, DeepSeek).
- Env-var naming mismatches: request references `GOOGLE_API_KEY`/`JWT_SECRET`/`FRONTEND_URL`/`BACKEND_URL`; code uses `GEMINI_API_KEY`/`SECRET_KEY`/`VITE_API_BASE_URL`/`CORS_ORIGINS`.

This document defines the requirements for restoring the system to a fully operational, validated state, organized so they map cleanly onto the 13 phases requested.

## Glossary
- **Verdict labels:** `TRUE`, `FALSE`, `MISLEADING`, `UNVERIFIED`, `INSUFFICIENT_DATA`.
- **Evidence card:** a retrieved source with title, URL, domain, snippet, relevance score, credibility score, and supporting/contradicting classification.
- **Provider chain:** the ordered set of search/LLM providers attempted with fallback.
- **Run mode:** Local development mode vs Docker Compose mode.

---

## Requirements

### Requirement 1: Project Audit Report (Phase 1)
**User Story:** As the project owner, I want an accurate, evidence-based audit of the real codebase, so that all subsequent fixes are based on facts rather than assumptions.

#### Acceptance Criteria
1. WHEN the audit is produced THEN it SHALL document the actual architecture, service dependencies, and required startup order based on the real code (not only the README/context docs).
2. WHEN the audit inspects retrieval THEN it SHALL identify that two retrieval stacks exist and which one each entrypoint (`main.py`, `agents.py`) uses.
3. WHEN the audit inspects Tavily THEN it SHALL explicitly state whether Tavily code exists and what is missing.
4. WHEN the audit inspects configuration THEN it SHALL list existing issues across Docker, API, environment variables, broken imports, missing dependencies, and port conflicts.
5. WHERE an env var named in the request does not match the code (`GOOGLE_API_KEY`, `JWT_SECRET`, `FRONTEND_URL`, `BACKEND_URL`) THE audit SHALL record the actual variable name used by the code.

### Requirement 2: Safe Cleanup of Running Services (Phase 2)
**User Story:** As the project owner, I want all project-related processes and Docker resources stopped and removed without touching unrelated work, so that I can start from a clean slate safely.

#### Acceptance Criteria
1. WHEN cleanup runs THEN it SHALL stop project processes: uvicorn, the project's python backend, and project node/npm/vite dev servers.
2. WHEN cleanup runs THEN it SHALL bring down the project's Docker Compose stack (`docker compose down`) and remove only this project's containers, networks, volumes, and images.
3. IF an Ollama process is running THEN cleanup SHALL NOT kill it unless it is project-specific, AND SHALL prefer leaving shared Ollama running.
4. THE cleanup SHALL NOT remove unrelated user containers, volumes, networks, or images.
5. WHEN cleanup completes THEN it SHALL produce a cleanup report listing exactly what was stopped/removed and what was deliberately preserved.
6. WHERE a destructive Docker removal (volumes/images) would occur THE system SHALL scope it to project-prefixed resources only.

### Requirement 3: Environment Validation & Correction (Phase 3)
**User Story:** As the project owner, I want every environment file validated and corrected, so that services start with consistent, valid configuration.

#### Acceptance Criteria
1. WHEN env files are inspected THEN the system SHALL check `backend/.env`, `backend/.env.example`, `.env.docker`, and `frontend/react-app/.env` for duplicates, missing values, invalid values, and conflicting values.
2. THE system SHALL verify the conceptual keys requested — `GOOGLE_API_KEY`/`GEMINI_API_KEY`, `TAVILY_API_KEY`, `NEO4J_URI`, `NEO4J_USERNAME`/`NEO4J_USER`, `NEO4J_PASSWORD`, `OLLAMA_BASE_URL`, `JWT_SECRET`/`SECRET_KEY`, `DATABASE_URL`, `FRONTEND_URL`/`VITE_API_BASE_URL`, `BACKEND_URL`/`CORS_ORIGINS` — and map each to the name the code actually reads.
3. WHEN a required value is a placeholder (e.g., `SECRET_KEY=replace-...`) THEN the system SHALL flag it and provide a corrected value or generation instruction.
4. WHEN `.env.docker` is validated THEN the system SHALL ensure `TAVILY_API_KEY` is present and that the LLM provider configuration is functional inside containers (no `GEMINI_API_KEY=DISABLED` left as the only reasoning provider unless Groq is valid).
5. THE system SHALL produce a corrections report describing each change and the rationale.
6. WHERE secrets are committed to the repo THE system SHALL flag them and recommend rotation/ignore handling without removing functionality required for local validation.

### Requirement 4: Tavily Integration (Phase 4)
**User Story:** As the project owner, I want Tavily search integrated into the retrieval pipeline, so that the system gains a reliable web-search evidence provider keyed by `TAVILY_API_KEY`.

#### Acceptance Criteria
1. THE system SHALL add the Tavily client dependency to `backend/requirements.txt` with a pinned version.
2. WHEN the backend starts THEN it SHALL load `TAVILY_API_KEY` from environment and report Tavily availability (present/missing) in logs at startup.
3. WHEN evidence retrieval runs for a claim THEN the retrieval pipeline SHALL query Tavily and incorporate its results into the merged candidate set alongside existing providers.
4. WHEN Tavily returns results THEN each result SHALL be normalized into the standard evidence-article shape (title, url, domain, content/snippet, published_date, credibility, source_type) used by the rest of the pipeline.
5. WHEN Tavily search executes THEN the system SHALL emit detailed logs: `TAVILY QUERY`, `TAVILY RESULTS COUNT`, `TAVILY SOURCES`, and a truncated `TAVILY RESPONSE`.
6. IF `TAVILY_API_KEY` is missing or Tavily errors THEN the pipeline SHALL degrade gracefully to the other providers without crashing.
7. THE Tavily results SHALL reach the agents (Defender/Prosecutor/Judge) as part of the evidence context, verifiable through pipeline logs.

### Requirement 5: Evidence Pipeline Audit & Tracing (Phase 5)
**User Story:** As the project owner, I want the full evidence pipeline traced with real data at each step, so that empty-evidence, filtering, and ranking bugs are found and fixed.

#### Acceptance Criteria
1. THE system SHALL trace the pipeline: User Claim → Query Generation → Tavily Search → Search Filtering → FAISS → Neo4j (optional) → Defender → Prosecutor → Judge → Verdict, printing actual data (counts and samples) at each step.
2. WHEN evidence is empty after filtering THEN the system SHALL log which stage removed the evidence and why (similarity, keyword, domain, credibility, age).
3. THE system SHALL select a single, consistent active retrieval path and ensure the API entrypoint and the agent graph use the same retrieval implementation OR document why they differ.
4. WHERE the advanced RAG path is intended THE system SHALL ensure `VERITAS_USE_ADVANCED_RAG` is set consistently with the chosen behavior and validated.
5. WHEN source ranking runs THEN supporting and contradicting evidence SHALL both be retained (the pipeline SHALL NOT discard all opposing evidence) so the Prosecutor and Defender each receive usable material.
6. WHEN the pipeline finishes THEN every retained evidence item SHALL be mapped to fields the frontend expects (no missing mappings between backend response and UI cards).

### Requirement 6: Agent Audit & Fixes (Phase 6)
**User Story:** As the project owner, I want the Defender, Prosecutor, and Judge agents verified and fixed, so that every verdict is backed by real adversarial reasoning.

#### Acceptance Criteria
1. THE system SHALL verify each agent's invocation, prompt construction, and response parsing for Defender, Prosecutor, and Judge.
2. WHEN an agent runs THEN it SHALL log `DEFENDER INPUT`/`DEFENDER OUTPUT`, `PROSECUTOR INPUT`/`PROSECUTOR OUTPUT`, and `JUDGE INPUT`/`JUDGE OUTPUT`.
3. IF an agent's LLM call fails (rate limit, timeout, parse error) THEN the system SHALL fall back per the provider chain and ultimately to deterministic stance logic, never returning an unhandled error to the API.
4. WHEN evidence exists THEN the Prosecutor SHALL produce contradicting arguments and the Defender SHALL produce supporting arguments (not "No evidence retrieved" when evidence is present).
5. WHEN the Judge runs THEN it SHALL synthesize a verdict and a meaningful confidence score (not a constant placeholder) consistent with the evidence and agent strengths.
6. THE agent outputs SHALL be structured so the frontend can render them (arguments list, strength, strongest point, evidence_count).

### Requirement 7: Frontend Audit & Mapping Fixes (Phase 7)
**User Story:** As the project owner, I want the frontend to correctly display all verification outputs, so that users see complete, accurate results.

#### Acceptance Criteria
1. THE frontend SHALL display: evidence cards, supporting evidence, contradicting evidence, Defender analysis, Prosecutor analysis, confidence score, claim statistics, and a working PDF download.
2. WHEN the backend returns a verification payload THEN the frontend field mappings SHALL match the backend response keys (verified against the real `/api/verify` response shape).
3. IF a field is absent in a response THEN the UI SHALL degrade gracefully (no crash, no blank screen) and show a clear empty state.
4. WHEN the user clicks Download PDF THEN the frontend SHALL call the correct backend PDF endpoint and receive a valid PDF.
5. THE frontend SHALL point to the correct backend base URL for the chosen run mode (local vs Docker).

### Requirement 8: Run Mode Decision (Phase 8)
**User Story:** As the project owner, I want a justified decision between Local and Docker run modes, so that we rebuild and run on the most stable architecture.

#### Acceptance Criteria
1. THE system SHALL evaluate Local development mode and Docker Compose mode against stability, reproducibility, LLM/provider reachability, and the broken `.venv` finding.
2. WHEN the decision is made THEN it SHALL be explicitly stated with reasoning and recorded in the design.
3. THE chosen mode SHALL be internally consistent with env files, ports, and frontend base URL.

### Requirement 9: Rebuild (Phase 9)
**User Story:** As the project owner, I want fresh, working builds with dependency issues fixed automatically, so that the system installs cleanly.

#### Acceptance Criteria
1. IF Docker mode is chosen THEN the system SHALL rebuild images, containers, and networks from scratch.
2. IF Local mode is chosen THEN the system SHALL create a working Python environment, install backend `requirements.txt` (including the new Tavily dependency), and install frontend dependencies.
3. WHEN a dependency conflict or missing package is detected THEN the system SHALL resolve it (pin/adjust versions) and document the change.
4. WHEN the rebuild completes THEN backend imports SHALL succeed (no `ModuleNotFoundError`) and the frontend SHALL build/lint without errors.

### Requirement 10: Start & Health Checks (Phase 10)
**User Story:** As the project owner, I want services started in the correct order and verified reachable, so that the system is confirmed live before testing.

#### Acceptance Criteria
1. WHEN starting THEN services SHALL start in dependency order (Ollama if used → backend → frontend; Neo4j only if enabled).
2. THE system SHALL verify reachability of: frontend, backend (`/api/health`), Ollama (if used), Neo4j (if enabled), and Tavily (key loaded + a successful test query).
3. WHEN `/api/health` is queried THEN it SHALL report provider/service status, and the system SHALL record the result.
4. IF a service is unreachable THEN the system SHALL diagnose and fix before proceeding to claim testing.

### Requirement 11: Automated Claim Testing (Phase 11)
**User Story:** As the project owner, I want all benchmark claims run automatically with full output, so that correctness is demonstrated.

#### Acceptance Criteria
1. THE system SHALL run all 8 claims automatically:
   - Claim 1: "Is India the least populated country in the world?" → expected FALSE
   - Claim 2: "Is Islam older than Hinduism?" → expected FALSE
   - Claim 3: "Is Earth flat?" → expected FALSE
   - Claim 4: "Did humans land on the moon?" → expected TRUE
   - Claim 5: "Is Bangalore the capital of Karnataka?" → expected TRUE
   - Claim 6: "Is Python a programming language?" → expected TRUE
   - Claim 7: "Did NEET 2026 paper leak before examination?" → evidence-based analysis (no hard-coded expected label)
   - Claim 8: "Is climate change a hoax?" → expected FALSE
2. FOR each claim THE system SHALL produce: retrieved sources, evidence count, supporting evidence, contradicting evidence, Defender output, Prosecutor output, Judge output, verdict, and confidence.
3. WHEN a claim has a defined expected verdict THEN the result SHALL be compared against it and recorded as pass/mismatch.
4. WHERE a verdict mismatches the expected label THE system SHALL record it and treat it as a quality issue for Phase 12 (subject to genuine evidence availability).

### Requirement 12: Quality Fix Loop (Phase 12)
**User Story:** As the project owner, I want quality issues fixed and re-tested until results are sound, so that the system is genuinely reliable.

#### Acceptance Criteria
1. IF any claim returns `UNVERIFIED`/`INSUFFICIENT_DATA` due to no evidence, missing prosecutor analysis, missing evidence, or missing sources THEN the system SHALL investigate and fix the root cause.
2. THE system SHALL repeat testing until, for claims with available real evidence: evidence cards appear, Prosecutor works, Defender works, Judge works, confidence is meaningful, and sources appear.
3. WHERE a claim legitimately lacks evidence (e.g., Claim 7) THE system SHALL still produce a coherent evidence-based analysis and a defensible verdict rather than an empty/error result.
4. THE system SHALL NOT stop after the first issue; it SHALL continue until the system is fully operational across all testable claims.

### Requirement 13: Final Report (Phase 13)
**User Story:** As the project owner, I want a complete final report, so that I understand everything that changed and the validation outcome.

#### Acceptance Criteria
1. THE final report SHALL include: root causes found, files modified, Docker changes, backend changes, frontend changes, environment changes, evidence retrieval fixes, agent fixes, commands used, and validation results.
2. THE report SHALL include the per-claim test outcomes from Phase 11 and the resolution of each Phase 12 issue.
3. THE report SHALL state the final run mode and how to start the system.

---

## Non-Functional & Safety Constraints
1. Cleanup SHALL be scoped to project resources only; unrelated Docker resources and shared Ollama SHALL be preserved.
2. Committed secrets SHALL be flagged; the system SHALL recommend rotation and proper ignore handling. No secret values SHALL be echoed unnecessarily in reports.
3. Network-exposed services created or modified SHALL have their auth/access posture noted (the backend currently relies on optional JWT; unauthenticated endpoints SHALL be acknowledged).
4. Changes SHALL be verified (backend imports succeed, frontend builds, health checks pass) before the system is declared operational.
5. The implementation SHALL prefer a single consistent retrieval path and avoid introducing a third parallel stack.
