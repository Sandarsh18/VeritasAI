from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor, wait
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler
from pydantic import BaseModel
import asyncio
import json
import os
import requests
import sys
import threading
import time

from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(__file__))

from agents.claim_analyzer import analyze_claim
from agents.prosecutor import run_prosecutor
from agents.defender import run_defender
from agents.judge import run_judge
from rag.evidence_retriever import retrieve_evidence
from rag.vector_store import get_index
from graph.neo4j_client import (
    store_claim,
    store_evidence_link,
    find_similar_claims,
    get_claim_network,
    get_all_claims,
    get_stats,
    is_connected,
)
from db.sqlite_store import save_claim as sqlite_save, load_claims, load_stats
from auth import get_optional_user
from database import User, UserClaim, SessionLocal, get_db
from rate_limit import limiter
from routers.auth_router import router as auth_router
from routers.user_router import router as user_router

AGENT_MODELS = {
    "prosecutor": "llama3.2:1b",
    "defender": "llama3.2:1b",
    "judge": "llama3.2:1b",
    "claim_analyzer": "llama3.2:1b",
}

PROSECUTOR_FALLBACK = {
    "arguments": ["No contradicting evidence retrieved due to timeout"],
    "strongest_point": "Timeout - unable to analyze",
}

DEFENDER_FALLBACK = {
    "arguments": ["No supporting evidence retrieved due to timeout"],
    "strongest_point": "Timeout - unable to analyze",
}

APP_START_TIME = time.time()


def _ts() -> str:
    return time.strftime("%H:%M:%S")


def warmup_models() -> None:
    models = sorted(set(AGENT_MODELS.values()))
    for model in models:
        try:
            print(f"[WARMUP] Loading {model}...")
            requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model,
                    "prompt": "ok",
                    "stream": False,
                    "keep_alive": "10m",
                    "options": {"num_predict": 1, "num_ctx": 128},
                },
                timeout=120,
            )
            print(f"[WARMUP] {model} ready ✅")
        except Exception as exc:
            print(f"[WARMUP] {model} failed: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    thread = threading.Thread(target=warmup_models, daemon=True)
    thread.start()
    yield


app = FastAPI(title="Fake News Verification API", version="1.0.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ClaimRequest(BaseModel):
    claim: str


def _extract_bearer(authorization: str | None) -> str | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    return authorization.split(" ", 1)[1].strip()


def check_ollama() -> bool:
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def check_faiss() -> bool:
    try:
        idx = get_index()
        return idx is not None
    except Exception:
        return False


def build_evidence_summary(evidence: list[dict]) -> str:
    return "\n".join(
        [
            f"- [{a.get('source', '')}] {a.get('title', '')} "
            f"(credibility: {a.get('credibility_score', 0.5)}): "
            f"{a.get('content', '')[:150]}"
            for a in evidence[:3]
        ]
    )


def run_parallel_agents(claim: str, evidence_summary: str) -> tuple[dict, dict]:
    prosecutor_result = PROSECUTOR_FALLBACK
    defender_result = DEFENDER_FALLBACK

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_prosecutor = executor.submit(run_prosecutor, claim, evidence_summary)
        future_defender = executor.submit(run_defender, claim, evidence_summary)

        done, _ = wait({future_prosecutor, future_defender}, timeout=150)

        if future_prosecutor in done:
            try:
                prosecutor_result = future_prosecutor.result()
            except Exception:
                prosecutor_result = PROSECUTOR_FALLBACK

        if future_defender in done:
            try:
                defender_result = future_defender.result()
            except Exception:
                defender_result = DEFENDER_FALLBACK

    return prosecutor_result, defender_result


async def run_pipeline(claim: str, quick: bool = False) -> dict:
    print(f"[{_ts()}] Starting: {claim[:50]}")

    if not quick:
        similar = await asyncio.to_thread(find_similar_claims, claim)
        if similar:
            cached = similar[0]
            if cached.get("text", "").lower() == claim.lower():
                return {
                    "cached": True,
                    "claim": claim,
                    "claim_id": cached["id"],
                    "verdict": cached.get("verdict", "UNVERIFIED"),
                    "confidence": cached.get("confidence", 35),
                    "reasoning": "Retrieved from knowledge graph cache",
                    "key_evidence": [],
                    "recommendation": "This claim has been previously analyzed.",
                    "claim_analysis": {},
                    "evidence": [],
                    "prosecutor": {"arguments": [], "strongest_point": ""},
                    "defender": {"arguments": [], "strongest_point": ""},
                }

    if not await asyncio.to_thread(check_ollama):
        raise HTTPException(status_code=503, detail="Ollama is not running.")

    try:
        claim_analysis = await asyncio.wait_for(
            asyncio.to_thread(analyze_claim, claim),
            timeout=15 if quick else 45,
        )
    except asyncio.TimeoutError:
        claim_analysis = {
            "category": "other",
            "claim_type": "factual",
            "entities": [],
            "keywords": claim.split()[:5],
            "complexity": "moderate",
            "potential_bias": "moderate",
        }

    evidence = []
    if not quick:
        try:
            evidence = await asyncio.wait_for(asyncio.to_thread(retrieve_evidence, claim, 3), timeout=45)
        except asyncio.TimeoutError:
            evidence = []

    print(f"[{_ts()}] RAG done: {len(evidence)} articles")

    credibility_scores = [float(item.get("credibility_score", 0.5)) for item in evidence]
    avg_credibility = (
        round(sum(credibility_scores) / len(credibility_scores), 2) if credibility_scores else 0.5
    )

    evidence_summary = build_evidence_summary(evidence)

    if quick:
        prosecutor_result = PROSECUTOR_FALLBACK
        defender_result = DEFENDER_FALLBACK
    else:
        prosecutor_result, defender_result = await asyncio.to_thread(
            run_parallel_agents, claim, evidence_summary
        )
        print(f"[{_ts()}] Prosecutor done")
        print(f"[{_ts()}] Defender done")

    try:
        judge_result = await asyncio.wait_for(
            asyncio.to_thread(run_judge, claim, prosecutor_result, defender_result, avg_credibility),
            timeout=75 if not quick else 15,
        )
    except asyncio.TimeoutError:
        judge_result = {
            "verdict": "UNVERIFIED",
            "confidence": 35,
            "reasoning": "Analysis timed out. Please retry.",
            "key_evidence": [],
            "recommendation": "Retry the claim for full analysis",
        }

    verdict = judge_result.get("verdict", "UNVERIFIED")
    confidence = int(judge_result.get("confidence", 35))
    if confidence == 60:
        confidence = 61
    confidence = max(30, min(97, confidence))
    print(f"[{_ts()}] Judge done: {verdict} {confidence}%")

    claim_id = None
    if quick:
        return {
            "cached": False,
            "claim": claim,
            "claim_id": None,
            "verdict": verdict,
            "confidence": confidence,
            "reasoning": judge_result.get("reasoning", ""),
            "key_evidence": judge_result.get("key_evidence", []),
            "recommendation": judge_result.get("recommendation", ""),
            "claim_analysis": claim_analysis,
            "evidence": [],
            "prosecutor": prosecutor_result,
            "defender": defender_result,
        }

    try:
        claim_id = await asyncio.to_thread(store_claim, claim, verdict, confidence)
        for ev in evidence:
            rel_type = "RELATED_TO"
            if ev.get("verdict") == "false":
                rel_type = "CONTRADICTED_BY"
            elif ev.get("verdict") == "true":
                rel_type = "SUPPORTED_BY"
            await asyncio.to_thread(
                store_evidence_link,
                claim_id,
                ev.get("id", "unknown"),
                rel_type,
                ev.get("title", ""),
                ev.get("source", ""),
            )
    except Exception as exc:
        print(f"Neo4j storage failed (non-critical): {exc}")

    try:
        sqlite_id = await asyncio.to_thread(sqlite_save, claim, verdict, confidence)
        if not claim_id:
            claim_id = sqlite_id
    except Exception as exc:
        print(f"SQLite storage failed: {exc}")

    return {
        "cached": False,
        "claim": claim,
        "claim_id": claim_id,
        "verdict": verdict,
        "confidence": confidence,
        "reasoning": judge_result.get("reasoning", ""),
        "key_evidence": judge_result.get("key_evidence", []),
        "recommendation": judge_result.get("recommendation", ""),
        "claim_analysis": claim_analysis,
        "evidence": evidence,
        "prosecutor": prosecutor_result,
        "defender": defender_result,
    }


@app.get("/health")
async def health():
    ollama_ok = await asyncio.to_thread(check_ollama)
    neo4j_ok = await asyncio.to_thread(is_connected)
    faiss_ok = await asyncio.to_thread(check_faiss)
    db_ok = True
    total_users = 0
    total_claims_verified = 0
    try:
        db = SessionLocal()
        total_users = db.query(User).count()
        total_claims_verified = db.query(UserClaim).count()
        db.close()
    except Exception:
        db_ok = False

    return {
        "status": "healthy" if (ollama_ok and faiss_ok and db_ok) else "degraded",
        "ollama": "connected" if ollama_ok else "disconnected",
        "neo4j": "connected" if neo4j_ok else "disconnected",
        "database": "connected" if db_ok else "disconnected",
        "faiss_index": "loaded" if faiss_ok else "not_loaded",
        "total_users": total_users,
        "total_claims_verified": total_claims_verified,
        "uptime_seconds": int(time.time() - APP_START_TIME),
        "models": {
            "prosecutor": "mistral",
            "defender": "phi3",
            "judge": "llama3",
        },
    }


@app.get("/api/models")
async def get_models():
    return AGENT_MODELS


@app.post("/api/verify")
@limiter.limit("10/hour")
async def verify_claim(
    request: Request,
    payload: ClaimRequest,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    claim = payload.claim.strip()
    if not claim:
        raise HTTPException(status_code=400, detail="Claim cannot be empty")
    if len(claim) < 10:
        raise HTTPException(status_code=400, detail="Claim too short")

    try:
        result = await asyncio.wait_for(run_pipeline(claim, quick=False), timeout=300)

        token = _extract_bearer(authorization)
        user = get_optional_user(token, db) if token else None
        if user:
            transcript = {
                "reasoning": result.get("reasoning"),
                "key_evidence": result.get("key_evidence", []),
                "recommendation": result.get("recommendation", ""),
                "prosecutor": result.get("prosecutor", {}),
                "defender": result.get("defender", {}),
                "evidence": result.get("evidence", []),
                "claim_analysis": result.get("claim_analysis", {}),
            }
            user_claim = UserClaim(
                user_id=user.id,
                claim_text=claim,
                verdict=result.get("verdict", "UNVERIFIED"),
                confidence=float(result.get("confidence", 0)),
                reasoning=json.dumps(transcript),
            )
            db.add(user_claim)
            user.total_claims = (user.total_claims or 0) + 1
            db.commit()
            db.refresh(user_claim)
            result["id"] = user_claim.id
            result["user_claim_id"] = user_claim.id
        else:
            result["id"] = result.get("claim_id")

        return result
    except asyncio.TimeoutError:
        return {
            "verdict": "UNVERIFIED",
            "confidence": 35,
            "reasoning": "Analysis took too long. Try a shorter claim.",
            "claim": claim,
            "error": "timeout",
        }


@app.post("/api/verify/quick")
async def verify_claim_quick(request: ClaimRequest):
    claim = request.claim.strip()
    if not claim:
        raise HTTPException(status_code=400, detail="Claim cannot be empty")
    if len(claim) < 5:
        raise HTTPException(status_code=400, detail="Claim too short")

    try:
        return await asyncio.wait_for(run_pipeline(claim, quick=True), timeout=60)
    except asyncio.TimeoutError:
        return {
            "verdict": "UNVERIFIED",
            "confidence": 35,
            "reasoning": "Quick analysis timed out. Please retry.",
            "claim": claim,
            "error": "timeout",
        }


@app.get("/api/claims/history")
async def get_history():
    try:
        claims = await asyncio.to_thread(get_all_claims, 20) if await asyncio.to_thread(is_connected) else []
        if not claims:
            claims = await asyncio.to_thread(load_claims, 20)
        return {"claims": claims}
    except Exception as exc:
        try:
            return {"claims": await asyncio.to_thread(load_claims, 20)}
        except Exception:
            return {"claims": [], "error": str(exc)}


@app.get("/api/graph/{claim_id}")
async def get_graph(claim_id: str):
    try:
        graph_data = await asyncio.to_thread(get_claim_network, claim_id)
        return graph_data
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/stats")
async def get_statistics():
    try:
        stats = await asyncio.to_thread(get_stats) if await asyncio.to_thread(is_connected) else {}
        if not stats or stats.get("total_claims", 0) == 0:
            stats = await asyncio.to_thread(load_stats)
        return stats
    except Exception as exc:
        try:
            return await asyncio.to_thread(load_stats)
        except Exception:
            return {
                "total_claims": 0,
                "verdict_distribution": {},
                "top_sources": [],
                "error": str(exc),
            }


app.include_router(auth_router, prefix="/api")
app.include_router(user_router, prefix="/api")
