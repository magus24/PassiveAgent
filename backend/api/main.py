import datetime

from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.future import select
from sqlalchemy import func, or_
from storage.db import get_session, Message, Alert, User, UserStat, UserNameHistory, AIMessageAnalysis
from analysis.embedding_engine import embedding_engine
from analysis.user_analytics import get_user_analytics
from graph.graph_builder import graph_builder
from sqlalchemy.ext.asyncio import AsyncSession
from config.settings import settings
from analysis.telegram_threat_patterns import telegram_threat_analyzer
from analysis.backfill import apply_local_analysis, backfill_local_analysis
from ai.ai_service import analyze_with_policy, build_ai_record

app = FastAPI(
    title="PassiveAgent API",
    description="Intelligence pipeline API for Telegram OSINT monitoring",
    version="2.0.0",
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def serialize_ai_analysis(analysis: AIMessageAnalysis | None):
    if not analysis:
        return None
    return {
        "id": analysis.id,
        "message_id": analysis.message_id,
        "provider": analysis.provider,
        "model": analysis.model,
        "label": analysis.label,
        "risk_level": analysis.risk_level,
        "risk_score": analysis.risk_score,
        "confidence": analysis.confidence,
        "summary": analysis.summary,
        "reasons": analysis.reasons or [],
        "detected_patterns": analysis.detected_patterns or [],
        "recommended_action": analysis.recommended_action,
        "raw_response": analysis.raw_response,
        "text_hash": analysis.text_hash,
        "status": analysis.status,
        "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
    }


def split_links(value: str | None) -> list[str]:
    return [url for url in (value or "").split(",") if url]


def serialize_message(msg: Message) -> dict:
    return {
        "id": msg.id,
        "telegram_id": msg.telegram_id,
        "user_id": msg.user_id,
        "chat_id": msg.chat_id,
        "channel_id": msg.channel_id,
        "sender_id": msg.sender_id,
        "text": msg.text,
        "links": msg.links,
        "message_type": msg.message_type,
        "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
        "risk_score": msg.risk_score,
        "risk_level": msg.risk_level,
        "reasons": msg.reasons or [],
        "classification_label": msg.classification_label,
        "classification_score": msg.classification_score,
        "local_score": msg.local_score,
        "local_category": msg.local_category,
        "local_reasons": msg.local_reasons or [],
        "extracted_entities": msg.extracted_entities or {},
        "campaign_key": msg.campaign_key,
        "review_status": msg.review_status,
        "review_note": msg.review_note,
        "reviewed_at": msg.reviewed_at.isoformat() if msg.reviewed_at else None,
        "ai_status": msg.ai_status,
        "ai_label": msg.ai_label,
        "ai_score": msg.ai_score,
        "ai_confidence": (msg.ai_analysis or {}).get("confidence") if msg.ai_analysis else None,
        "ai_summary": (msg.ai_analysis or {}).get("summary") if msg.ai_analysis else None,
        "ai_risk_level": (msg.ai_analysis or {}).get("risk_level") if msg.ai_analysis else None,
        "ai_analysis": msg.ai_analysis,
    }


async def run_ai_for_message(
    message: Message,
    session: AsyncSession,
    *,
    force: bool = False,
) -> tuple[dict | None, str]:
    urls = split_links(message.links)
    local_result = {
        "local_score": message.local_score,
        "category": message.local_category,
        "reasons": message.local_reasons or [],
        "text_hash": message.text_hash,
    }
    if not message.text_hash or message.local_score is None:
        apply_local_analysis(message)
        local_result = {
            "local_score": message.local_score,
            "category": message.local_category,
            "reasons": message.local_reasons or [],
            "text_hash": message.text_hash,
        }

    local_score = float(message.local_score or 0.0)
    if local_score >= settings.AI_MIN_LOCAL_SCORE:
        message.risk_score = round(max(message.risk_score or 0.0, local_score), 4)
        message.risk_level = "HIGH" if message.risk_score >= 0.7 else "MEDIUM" if message.risk_score >= 0.4 else "LOW"
        existing_reasons = list(message.reasons or [])
        for reason in message.local_reasons or []:
            if reason not in existing_reasons:
                existing_reasons.append(reason)
        message.reasons = existing_reasons

    classification = {
        "label": message.classification_label,
        "score": message.classification_score or 0.0,
    }
    ai_result, ai_status = await analyze_with_policy(
        session=session,
        message_text=message.text or "",
        text_hash=local_result.get("text_hash"),
        local_result=local_result,
        metadata={
            "message_id": message.id,
            "telegram_id": message.telegram_id,
            "sender_id": message.sender_id,
            "chat_id": message.chat_id,
            "channel_id": message.channel_id,
            "urls": urls,
            "message_type": message.message_type,
            "current_risk_score": message.risk_score,
            "current_risk_level": message.risk_level,
            "local_result": local_result,
        },
        classification=classification,
        force=force,
    )

    message.ai_status = ai_status
    if ai_result:
        message.ai_analysis = ai_result
        message.ai_score = ai_result.get("risk_score")
        message.ai_label = ai_result.get("label")
        session.add(build_ai_record(
            message_id=message.id,
            text_hash=local_result.get("text_hash"),
            ai_result=ai_result,
            status=ai_status,
        ))
        if ai_result.get("confidence", 0) > 0:
            ai_norm = max(0.0, min(1.0, (ai_result.get("risk_score") or 0) / 100.0))
            combined_score = (message.risk_score or 0.0) * 0.65 + ai_norm * 0.35
            if ai_result.get("risk_level") == "critical":
                combined_score = max(combined_score, 0.85)
            message.risk_score = round(max(0.0, min(1.0, combined_score)), 4)
            message.risk_level = "HIGH" if message.risk_score >= 0.7 else "MEDIUM" if message.risk_score >= 0.4 else "LOW"

    return ai_result, ai_status


# ── Root ────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "PassiveAgent API v2.0 is running"}


@app.get("/ai/status")
async def ai_status():
    return {
        "enabled": settings.AI_ENABLED,
        "provider": settings.AI_PROVIDER,
        "model": settings.GROQ_MODEL,
        "api_key_configured": bool(settings.GROQ_API_KEY),
        "daily_limit": settings.AI_DAILY_LIMIT,
        "per_minute_limit": settings.AI_PER_MINUTE_LIMIT,
        "min_local_score": settings.AI_MIN_LOCAL_SCORE,
        "analyze_only_candidates": settings.AI_ANALYZE_ONLY_CANDIDATES,
    }


@app.get("/messages/{message_id}/ai-analysis")
async def get_message_ai_analysis(
    message_id: int,
    session: AsyncSession = Depends(get_session),
):
    message_result = await session.execute(select(Message).where(Message.id == message_id))
    message = message_result.scalar_one_or_none()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    result = await session.execute(
        select(AIMessageAnalysis)
        .where(AIMessageAnalysis.message_id == message_id)
        .order_by(AIMessageAnalysis.created_at.desc())
    )
    analysis = result.scalars().first()
    if analysis:
        return serialize_ai_analysis(analysis)
    if message.ai_analysis:
        return message.ai_analysis
    raise HTTPException(status_code=404, detail="AI analysis not found")


@app.post("/messages/{message_id}/reanalyze-ai")
async def reanalyze_message_ai(
    message_id: int,
    session: AsyncSession = Depends(get_session),
):
    message_result = await session.execute(select(Message).where(Message.id == message_id))
    message = message_result.scalar_one_or_none()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    ai_result, ai_status = await run_ai_for_message(message, session, force=False)
    await session.commit()
    return {
        "message_id": message.id,
        "ai_status": ai_status,
        "analysis": ai_result,
    }


@app.post("/ai/reanalyze-candidates")
async def reanalyze_ai_candidates(
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    query = (
        select(Message)
        .where(
            or_(Message.ai_status.is_(None), Message.ai_status.in_(["not_evaluated", "skipped_low_risk", "failed"])),
            or_(
                Message.local_score >= settings.AI_MIN_LOCAL_SCORE,
                Message.local_score.is_(None),
                Message.classification_label.in_(["scam", "phishing", "spam"]),
            ),
        )
        .order_by(Message.timestamp.desc())
        .limit(limit)
    )
    result = await session.execute(query)
    messages = result.scalars().all()

    stats = {
        "selected": len(messages),
        "analyzed": 0,
        "cached": 0,
        "skipped": 0,
        "failed": 0,
        "rate_limited": 0,
        "items": [],
    }
    for message in messages:
        ai_result, ai_status = await run_ai_for_message(message, session, force=False)
        if ai_status == "analyzed":
            stats["analyzed"] += 1
        elif ai_status == "cached":
            stats["cached"] += 1
        elif ai_status == "failed":
            stats["failed"] += 1
        elif ai_status.startswith("rate_limited"):
            stats["rate_limited"] += 1
            stats["items"].append({"message_id": message.id, "ai_status": ai_status})
            break
        else:
            stats["skipped"] += 1
        stats["items"].append({
            "message_id": message.id,
            "ai_status": ai_status,
            "label": ai_result.get("label") if ai_result else None,
            "risk_score": ai_result.get("risk_score") if ai_result else None,
        })

    await session.commit()
    return stats


@app.post("/maintenance/backfill-local")
async def backfill_local(
    limit: int = Query(500, ge=1, le=5000),
    session: AsyncSession = Depends(get_session),
):
    return await backfill_local_analysis(session, limit=limit)


@app.get("/messages/{message_id}")
async def get_message_detail(
    message_id: int,
    session: AsyncSession = Depends(get_session),
):
    message_result = await session.execute(select(Message).where(Message.id == message_id))
    message = message_result.scalar_one_or_none()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    similar_count = 0
    campaign_count = 0
    if message.text_hash:
        similar_result = await session.execute(
            select(func.count(Message.id)).where(Message.text_hash == message.text_hash)
        )
        similar_count = similar_result.scalar() or 0
    if message.campaign_key:
        campaign_result = await session.execute(
            select(func.count(Message.id)).where(Message.campaign_key == message.campaign_key)
        )
        campaign_count = campaign_result.scalar() or 0

    return {
        "message": serialize_message(message),
        "similar_text_count": similar_count,
        "campaign_count": campaign_count,
    }


@app.patch("/messages/{message_id}/review")
async def update_message_review(
    message_id: int,
    status: str = Query(..., description="new | needs_review | confirmed_threat | false_positive | ignored"),
    note: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    allowed = {"new", "needs_review", "confirmed_threat", "false_positive", "ignored"}
    if status not in allowed:
        raise HTTPException(status_code=400, detail="Invalid review status")

    message_result = await session.execute(select(Message).where(Message.id == message_id))
    message = message_result.scalar_one_or_none()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    message.review_status = status
    message.review_note = note
    message.reviewed_at = datetime.datetime.utcnow()
    await session.commit()
    return serialize_message(message)


# ── Messages ────────────────────────────────────────────────────────────

@app.get("/messages")
async def get_messages(
    limit: int = Query(100, ge=1, le=1000),
    risk_level: str | None = Query(None, description="Filter by risk level: LOW, MEDIUM, HIGH"),
    classification: str | None = Query(None, description="Filter by classification: scam, phishing, spam, normal"),
    ai_status: str | None = Query(None, description="Filter by AI status"),
    local_category: str | None = Query(None, description="Filter by local category"),
    review_status: str | None = Query(None, description="Filter by review status"),
    needs_review: bool | None = Query(None, description="Show candidate messages that need analyst review"),
    has_link: bool | None = Query(None, description="Filter by link presence"),
    min_risk: float | None = Query(None, ge=0, le=1, description="Minimum final risk score"),
    session: AsyncSession = Depends(get_session),
):
    """Get messages with enriched intelligence data.

    Returns messages ordered by timestamp (newest first) with all enriched
    fields: risk_score, risk_level, classification_label, classification_score.
    Embeddings are excluded from the response for performance.
    """
    query = select(Message)

    if risk_level:
        query = query.where(Message.risk_level == risk_level.upper())
    if classification:
        query = query.where(Message.classification_label == classification.lower())
    if ai_status:
        query = query.where(Message.ai_status == ai_status)
    if local_category:
        query = query.where(Message.local_category == local_category)
    if review_status:
        query = query.where(Message.review_status == review_status)
    if needs_review:
        query = query.where(
            or_(
                Message.review_status == "needs_review",
                Message.risk_score >= 0.4,
                Message.local_score >= settings.AI_MIN_LOCAL_SCORE,
                Message.classification_label.in_(["scam", "phishing", "spam"]),
            )
        )
    if has_link is not None:
        query = query.where(Message.has_link == has_link)
    if min_risk is not None:
        query = query.where(Message.risk_score >= min_risk)

    query = query.order_by(Message.timestamp.desc()).limit(limit)
    result = await session.execute(query)
    messages = result.scalars().all()

    return [
        {
            **serialize_message(msg),
        }
        for msg in messages
    ]


# ── Alerts ──────────────────────────────────────────────────────────────

@app.get("/alerts")
async def get_alerts(
    limit: int = Query(100, ge=1, le=1000),
    resolved: bool | None = Query(None, description="Filter by resolved status"),
    session: AsyncSession = Depends(get_session),
):
    """Get alerts from the Alert table with full detail.

    Alerts are created when a message reaches HIGH risk level.
    """
    query = select(Alert)

    if resolved is not None:
        query = query.where(Alert.resolved == resolved)

    query = query.order_by(Alert.timestamp.desc()).limit(limit)
    result = await session.execute(query)
    alerts = result.scalars().all()

    return [
        {
            "id": alert.id,
            "message_telegram_id": alert.message_telegram_id,
            "channel_id": alert.channel_id,
            "sender_id": alert.sender_id,
            "text_preview": alert.text_preview,
            "risk_score": alert.risk_score,
            "risk_level": alert.risk_level,
            "classification_label": alert.classification_label,
            "classification_score": alert.classification_score,
            "timestamp": alert.timestamp.isoformat() if alert.timestamp else None,
            "resolved": alert.resolved,
        }
        for alert in alerts
    ]


@app.patch("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Mark an alert as resolved."""
    result = await session.execute(
        select(Alert).where(Alert.id == alert_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.resolved = True
    await session.commit()
    return {"status": "resolved", "alert_id": alert_id}


# ── Semantic Similarity Search (pgvector) ───────────────────────────────

@app.get("/similar")
async def get_similar_messages(
    message_id: int = Query(..., description="Database ID of the reference message"),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """Find semantically similar messages using pgvector cosine distance.

    Uses indexed vector similarity search — fast even at 100k+ messages.
    Replaces the previous O(N) brute-force Python implementation.
    """
    # 1. Get the reference message embedding
    ref_result = await session.execute(
        select(Message.embedding).where(Message.id == message_id)
    )
    ref_row = ref_result.first()
    if ref_row is None:
        raise HTTPException(status_code=404, detail="Message not found")

    ref_embedding = ref_row[0]
    if ref_embedding is None:
        raise HTTPException(
            status_code=400,
            detail="Reference message has no embedding",
        )

    # 2. pgvector cosine distance query
    distance_expr = Message.embedding.cosine_distance(ref_embedding)
    query = (
        select(Message, distance_expr.label("distance"))
        .where(Message.embedding.isnot(None), Message.id != message_id)
        .order_by(distance_expr)
        .limit(limit)
    )
    result = await session.execute(query)
    rows = result.all()

    return [
        {
            "id": msg.id,
            "telegram_id": msg.telegram_id,
            "channel_id": msg.channel_id,
            "sender_id": msg.sender_id,
            "text": msg.text,
            "similarity_score": round(1.0 - distance, 4),
            "risk_score": msg.risk_score,
            "risk_level": msg.risk_level,
            "classification_label": msg.classification_label,
            "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
        }
        for msg, distance in rows
    ]


# ── Dashboard Stats ─────────────────────────────────────────────────────

@app.get("/stats")
async def get_stats(session: AsyncSession = Depends(get_session)):
    """Dashboard statistics: total messages, alert counts, risk distribution.

    Provides an at-a-glance overview of the intelligence pipeline state.
    """
    # Total messages
    total_result = await session.execute(select(func.count(Message.id)))
    total_messages = total_result.scalar() or 0

    # Risk level distribution
    risk_dist_result = await session.execute(
        select(Message.risk_level, func.count(Message.id))
        .group_by(Message.risk_level)
    )
    risk_distribution = {
        row[0]: row[1] for row in risk_dist_result.all()
    }

    # Classification distribution
    class_dist_result = await session.execute(
        select(Message.classification_label, func.count(Message.id))
        .where(Message.classification_label.isnot(None))
        .group_by(Message.classification_label)
    )
    classification_distribution = {
        row[0]: row[1] for row in class_dist_result.all()
    }

    review_dist_result = await session.execute(
        select(Message.review_status, func.count(Message.id))
        .group_by(Message.review_status)
    )
    review_distribution = {
        row[0] or "new": row[1] for row in review_dist_result.all()
    }

    local_dist_result = await session.execute(
        select(Message.local_category, func.count(Message.id))
        .where(Message.local_category.isnot(None))
        .group_by(Message.local_category)
    )
    local_distribution = {
        row[0]: row[1] for row in local_dist_result.all()
    }

    # Alert stats
    total_alerts_result = await session.execute(select(func.count(Alert.id)))
    total_alerts = total_alerts_result.scalar() or 0

    unresolved_alerts_result = await session.execute(
        select(func.count(Alert.id)).where(Alert.resolved == False)
    )
    unresolved_alerts = unresolved_alerts_result.scalar() or 0

    # Unique channels and senders
    channels_result = await session.execute(
        select(func.count(func.distinct(Message.channel_id)))
    )
    unique_channels = channels_result.scalar() or 0

    senders_result = await session.execute(
        select(func.count(func.distinct(Message.sender_id)))
    )
    unique_senders = senders_result.scalar() or 0

    return {
        "total_messages": total_messages,
        "unique_channels": unique_channels,
        "unique_senders": unique_senders,
        "risk_distribution": risk_distribution,
        "classification_distribution": classification_distribution,
        "review_distribution": review_distribution,
        "local_distribution": local_distribution,
        "needs_review": review_distribution.get("needs_review", 0),
        "confirmed_threats": review_distribution.get("confirmed_threat", 0),
        "total_alerts": total_alerts,
        "unresolved_alerts": unresolved_alerts,
    }


# ── Users ───────────────────────────────────────────────────────────────

@app.get("/users")
async def get_users(
    limit: int = Query(100, ge=1, le=1000),
    search: str | None = Query(None, description="Search by name or username"),
    session: AsyncSession = Depends(get_session),
):
    """Get list of all users with their basic stats."""
    query = select(User, UserStat).outerjoin(UserStat, User.id == UserStat.user_id)
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            User.username.ilike(search_term) | 
            User.first_name.ilike(search_term) | 
            User.last_name.ilike(search_term)
        )
        
    query = query.order_by(User.created_at.desc()).limit(limit)
    result = await session.execute(query)
    rows = result.all()
    
    users = []
    for user, stat in rows:
        users.append({
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "total_messages": stat.total_messages if stat else 0,
            "risk_score": stat.risk_score if stat else 0.0,
        })
        
    return users

@app.get("/user/{user_id}")
async def get_user_profile(user_id: int, session: AsyncSession = Depends(get_session)):
    """Get full user profile including stats and name history."""
    user_result = await session.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    stat_result = await session.execute(select(UserStat).where(UserStat.user_id == user_id))
    stat = stat_result.scalar_one_or_none()
    
    history_result = await session.execute(
        select(UserNameHistory).where(UserNameHistory.user_id == user_id).order_by(UserNameHistory.timestamp.desc())
    )
    history = [{"name": h.name, "timestamp": h.timestamp.isoformat() if h.timestamp else None} for h in history_result.scalars().all()]
    
    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "created_at": user.created_at.isoformat() if user.created_at else None
        },
        "stats": {
            "total_messages": stat.total_messages if stat else 0,
            "total_chats": stat.total_chats if stat else 0,
            "media_percent": stat.media_percent if stat else 0.0,
            "reply_percent": stat.reply_percent if stat else 0.0,
            "favorite_chat": stat.favorite_chat if stat else None,
            "risk_score": stat.risk_score if stat else 0.0,
        },
        "names_history": history
    }

@app.get("/user/{user_id}/messages")
async def get_user_messages(
    user_id: int, 
    type: str = Query(None, description="Filter by message type"),
    chat_id: int = Query(None, description="Filter by chat ID"),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session)
):
    """Get all messages sent by a specific user with filtering options."""
    query = select(Message).where(Message.user_id == user_id)
    
    if type:
        query = query.where(Message.message_type == type)
    if chat_id:
        query = query.where(Message.chat_id == chat_id)
        
    query = query.order_by(Message.timestamp.desc()).limit(limit)
    result = await session.execute(query)
    messages = result.scalars().all()
    
    return [
        {
            "id": msg.id,
            "telegram_id": msg.telegram_id,
            "chat_id": msg.chat_id,
            "text": msg.text,
            "message_type": msg.message_type,
            "has_media": msg.has_media,
            "has_link": msg.has_link,
            "is_reply": msg.is_reply,
            "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
            "risk_score": msg.risk_score,
            "risk_level": msg.risk_level,
            "reasons": msg.reasons,
            "local_score": msg.local_score,
            "local_category": msg.local_category,
            "local_reasons": msg.local_reasons or [],
            "ai_status": msg.ai_status,
            "ai_label": msg.ai_label,
            "ai_score": msg.ai_score,
            "ai_analysis": msg.ai_analysis,
        }
        for msg in messages
    ]

@app.get("/user/{user_id}/analytics")
async def get_user_analytics_api(user_id: int, session: AsyncSession = Depends(get_session)):
    """Get advanced analytics for a specific user (message distribution, top chats, word freq)."""
    user_result = await session.execute(select(User).where(User.id == user_id))
    if not user_result.scalar_one_or_none():
         raise HTTPException(status_code=404, detail="User not found")
         
    analytics = await get_user_analytics(user_id, session)
    return analytics



# ── Graph ───────────────────────────────────────────────────────────────

@app.get("/graph")
async def get_graph_data():
    """Get Neo4j graph data showing relationships between users, channels, and links.

    Reuses the shared graph_builder driver instead of creating a new one per request.
    """
    query = "MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 100"

    graph_data = []
    async with graph_builder.driver.session() as session:
        result = await session.run(query)
        async for record in result:
            graph_data.append({
                "source": dict(record["n"]),
                "relationship": type(record["r"]).__name__,
                "target": dict(record["m"]),
            })
    return {"nodes_and_edges": graph_data}
