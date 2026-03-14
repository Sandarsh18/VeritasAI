import json
import secrets
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from statistics import mean
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_
from sqlalchemy.orm import Session

from auth import get_current_user
from database import UserClaim, UserFeedback, get_db
from db.sqlite_store import load_claims

router = APIRouter(tags=["users"])

SHARED_TOKENS: dict[str, int] = {}


class FeedbackRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None


def _extract_bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    return authorization.split(" ", 1)[1].strip()


def _require_user(authorization: Optional[str], db: Session):
    token = _extract_bearer(authorization)
    user = get_current_user(token, db) if token else None
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user


@router.get("/user/claims")
def get_user_claims(
    verdict: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _require_user(authorization, db)
    query = db.query(UserClaim).filter(UserClaim.user_id == user.id)
    if verdict:
        query = query.filter(UserClaim.verdict == verdict.upper())

    if date_from:
        try:
            query = query.filter(UserClaim.created_at >= datetime.fromisoformat(date_from))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid date_from format") from exc
    if date_to:
        try:
            query = query.filter(UserClaim.created_at <= datetime.fromisoformat(date_to))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid date_to format") from exc

    total = query.count()
    rows = (
        query.order_by(UserClaim.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    claims = [
        {
            "id": c.id,
            "text": c.claim_text,
            "verdict": c.verdict,
            "confidence": c.confidence,
            "date": c.created_at.isoformat() if c.created_at else None,
            "bookmarked": c.is_bookmarked,
        }
        for c in rows
    ]
    return {"claims": claims, "page": page, "limit": limit, "total": total}


@router.get("/user/claims/{claim_id}")
def get_user_claim_detail(
    claim_id: int,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _require_user(authorization, db)
    claim = db.query(UserClaim).filter(and_(UserClaim.id == claim_id, UserClaim.user_id == user.id)).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    parsed_reasoning = claim.reasoning
    try:
        parsed_reasoning = json.loads(claim.reasoning) if claim.reasoning else {}
    except json.JSONDecodeError:
        parsed_reasoning = {"reasoning": claim.reasoning}

    return {
        "id": claim.id,
        "text": claim.claim_text,
        "verdict": claim.verdict,
        "confidence": claim.confidence,
        "created_at": claim.created_at.isoformat() if claim.created_at else None,
        "bookmarked": claim.is_bookmarked,
        "transcript": parsed_reasoning,
    }


@router.post("/user/claims/{claim_id}/bookmark")
def toggle_bookmark(
    claim_id: int,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _require_user(authorization, db)
    claim = db.query(UserClaim).filter(and_(UserClaim.id == claim_id, UserClaim.user_id == user.id)).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    claim.is_bookmarked = not claim.is_bookmarked
    db.commit()
    return {"message": "Bookmark updated", "bookmarked": claim.is_bookmarked}


@router.delete("/user/claims/{claim_id}")
def delete_user_claim(
    claim_id: int,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _require_user(authorization, db)
    claim = db.query(UserClaim).filter(and_(UserClaim.id == claim_id, UserClaim.user_id == user.id)).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    db.delete(claim)
    if user.total_claims > 0:
        user.total_claims -= 1
    db.commit()
    return {"message": "Claim deleted"}


@router.get("/user/stats")
def user_stats(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _require_user(authorization, db)
    claims = db.query(UserClaim).filter(UserClaim.user_id == user.id).all()
    verdict_breakdown = Counter([c.verdict for c in claims if c.verdict])
    daily_counts = Counter([(c.created_at.date().isoformat() if c.created_at else "unknown") for c in claims])
    weekday_counter = Counter([(c.created_at.strftime("%A") if c.created_at else "Unknown") for c in claims])
    confidences = [float(c.confidence) for c in claims if c.confidence is not None]
    bookmarked_count = sum(1 for c in claims if c.is_bookmarked)

    trend = [{"date": day, "count": count} for day, count in sorted(daily_counts.items())]
    most_active_day = weekday_counter.most_common(1)[0][0] if weekday_counter else None
    return {
        "total_claims": len(claims),
        "verdict_breakdown": dict(verdict_breakdown),
        "accuracy_trend": trend,
        "most_active_day": most_active_day,
        "avg_confidence": round(mean(confidences), 2) if confidences else 0,
        "bookmarked_count": bookmarked_count,
    }


@router.post("/feedback/{claim_id}")
def submit_feedback(
    claim_id: int,
    payload: FeedbackRequest,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _require_user(authorization, db)
    claim = db.query(UserClaim).filter(and_(UserClaim.id == claim_id, UserClaim.user_id == user.id)).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    feedback = UserFeedback(user_id=user.id, claim_id=claim_id, rating=payload.rating, comment=payload.comment)
    db.add(feedback)
    db.commit()
    return {"message": "Feedback submitted"}


@router.get("/feedback/{claim_id}")
def get_feedback(claim_id: int, db: Session = Depends(get_db)):
    feedback_rows = db.query(UserFeedback).filter(UserFeedback.claim_id == claim_id).all()
    ratings = [item.rating for item in feedback_rows if item.rating is not None]
    comments = [
        {
            "user_id": item.user_id,
            "comment": item.comment,
            "rating": item.rating,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in feedback_rows
        if item.comment
    ]
    avg_rating = round(mean(ratings), 2) if ratings else 0
    return {"claim_id": claim_id, "avg_rating": avg_rating, "ratings_count": len(ratings), "comments": comments}


@router.post("/claims/{claim_id}/share")
def share_claim(
    claim_id: int,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _require_user(authorization, db)
    claim = db.query(UserClaim).filter(and_(UserClaim.id == claim_id, UserClaim.user_id == user.id)).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    claim.is_shared = True
    token = secrets.token_urlsafe(18)
    SHARED_TOKENS[token] = claim_id
    db.commit()
    return {"share_url": f"/shared/{token}", "token": token}


@router.get("/shared/{token}")
def get_shared_claim(token: str, db: Session = Depends(get_db)):
    claim_id = SHARED_TOKENS.get(token)
    if not claim_id:
        raise HTTPException(status_code=404, detail="Invalid or expired share token")

    claim = db.query(UserClaim).filter(UserClaim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    transcript = claim.reasoning
    try:
        transcript = json.loads(claim.reasoning) if claim.reasoning else {}
    except json.JSONDecodeError:
        transcript = {"reasoning": claim.reasoning}

    return {
        "id": claim.id,
        "claim": claim.claim_text,
        "verdict": claim.verdict,
        "confidence": claim.confidence,
        "created_at": claim.created_at.isoformat() if claim.created_at else None,
        "transcript": transcript,
    }


@router.get("/trending")
def get_trending(db: Session = Depends(get_db)):
    week_ago = datetime.utcnow() - timedelta(days=7)
    user_claims = db.query(UserClaim).filter(UserClaim.created_at >= week_ago).all()

    counter: dict[str, dict] = defaultdict(lambda: {"count": 0, "verdict": "UNVERIFIED", "confidence": 0})
    for item in user_claims:
        key = (item.claim_text or "").strip().lower()
        if not key:
            continue
        counter[key]["count"] += 1
        counter[key]["verdict"] = item.verdict or "UNVERIFIED"
        counter[key]["confidence"] = int(item.confidence or 0)

    trending = sorted(
        [
            {
                "claim": text,
                "verdict": payload["verdict"],
                "confidence": payload["confidence"],
                "verification_count": payload["count"],
            }
            for text, payload in counter.items()
        ],
        key=lambda x: x["verification_count"],
        reverse=True,
    )[:10]

    grouped = defaultdict(list)
    for row in trending:
        grouped[row["verdict"]].append(row)

    return {"claims": trending, "grouped_by_verdict": dict(grouped)}


@router.get("/search")
def search_claims(
    q: str,
    verdict: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query_text = q.strip().lower()
    if not query_text:
        return {"results": [], "total": 0, "page": page, "limit": limit}

    user_rows = db.query(UserClaim).all()
    matched = []
    for item in user_rows:
        if query_text in (item.claim_text or "").lower():
            if verdict and (item.verdict or "").upper() != verdict.upper():
                continue
            matched.append(
                {
                    "id": item.id,
                    "text": item.claim_text,
                    "verdict": item.verdict,
                    "confidence": item.confidence,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                    "scope": "user",
                }
            )

    global_rows = load_claims(500)
    for item in global_rows:
        text = item.get("text", "")
        if query_text in text.lower():
            if verdict and (item.get("verdict", "").upper() != verdict.upper()):
                continue
            matched.append(
                {
                    "id": item.get("id"),
                    "text": text,
                    "verdict": item.get("verdict"),
                    "confidence": item.get("confidence"),
                    "created_at": item.get("timestamp"),
                    "scope": "global",
                }
            )

    matched.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    total = len(matched)
    start = (page - 1) * limit
    end = start + limit
    return {"results": matched[start:end], "total": total, "page": page, "limit": limit}
