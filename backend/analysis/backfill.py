from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from analysis.entity_extractor import entity_extractor
from analysis.telegram_threat_patterns import telegram_threat_analyzer
from config.settings import settings
from storage.db import Message


def risk_level(score: float) -> str:
    if score >= 0.7:
        return "HIGH"
    if score >= 0.4:
        return "MEDIUM"
    return "LOW"


def apply_local_analysis(message: Message) -> dict:
    links = [url for url in (message.links or "").split(",") if url]
    local_result = telegram_threat_analyzer.analyze(message.text or "", links)
    entities = entity_extractor.extract(message.text or "", links)
    campaign_key = entity_extractor.campaign_key(local_result.get("text_hash"), entities)

    message.local_score = local_result.get("local_score")
    message.local_category = local_result.get("category")
    message.local_reasons = local_result.get("reasons")
    message.text_hash = local_result.get("text_hash")
    message.extracted_entities = entities
    message.campaign_key = campaign_key

    if message.local_score and message.local_score >= settings.AI_MIN_LOCAL_SCORE:
        message.risk_score = round(max(message.risk_score or 0.0, message.local_score), 4)
        message.risk_level = risk_level(message.risk_score)
        reasons = list(message.reasons or [])
        for reason in message.local_reasons or []:
            if reason not in reasons:
                reasons.append(reason)
        message.reasons = reasons
        if message.review_status in {None, "", "new"} and message.risk_score >= 0.4:
            message.review_status = "needs_review"
    elif not message.review_status:
        message.review_status = "new"

    return local_result


async def backfill_local_analysis(session: AsyncSession, limit: int = 500) -> dict:
    result = await session.execute(
        select(Message)
        .where(
            (Message.local_score.is_(None))
            | (Message.extracted_entities.is_(None))
            | (Message.review_status.is_(None))
        )
        .order_by(Message.timestamp.desc())
        .limit(limit)
    )
    messages = result.scalars().all()
    updated = 0
    needs_review = 0
    for message in messages:
        apply_local_analysis(message)
        updated += 1
        if message.review_status == "needs_review":
            needs_review += 1
    await session.commit()
    return {
        "selected": len(messages),
        "updated": updated,
        "needs_review": needs_review,
    }
