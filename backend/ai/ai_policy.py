import datetime
import logging
from collections import deque

from sqlalchemy import func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from config.settings import settings
from storage.db import AIMessageAnalysis

logger = logging.getLogger(__name__)


class AIRateLimiter:
    def __init__(self):
        self.minute_calls = deque()

    async def can_call(self, session: AsyncSession) -> tuple[bool, str]:
        if not settings.AI_ENABLED:
            return False, "disabled"
        if not settings.GROQ_API_KEY:
            return False, "missing_api_key"

        now = datetime.datetime.utcnow()
        minute_cutoff = now - datetime.timedelta(seconds=60)
        while self.minute_calls and self.minute_calls[0] < minute_cutoff:
            self.minute_calls.popleft()

        if len(self.minute_calls) >= settings.AI_PER_MINUTE_LIMIT:
            return False, "rate_limited_minute"

        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        result = await session.execute(
            select(func.count(AIMessageAnalysis.id)).where(
                AIMessageAnalysis.provider == "groq",
                AIMessageAnalysis.status == "analyzed",
                AIMessageAnalysis.created_at >= day_start,
            )
        )
        calls_today = result.scalar() or 0
        if calls_today >= settings.AI_DAILY_LIMIT:
            return False, "rate_limited_daily"

        return True, "allowed"

    def record_call(self):
        self.minute_calls.append(datetime.datetime.utcnow())


class AIEligibilityPolicy:
    def should_analyze(
        self,
        *,
        text: str,
        local_result: dict,
        classification: dict | None = None,
        repetition_score: float = 0.0,
        graph_score: float = 0.0,
        force: bool = False,
    ) -> tuple[bool, str]:
        if not settings.AI_ANALYZE_ONLY_CANDIDATES or force:
            return True, "forced"

        if not text or len(text.strip()) < 10:
            return False, "skipped_too_short"

        local_score = float(local_result.get("local_score") or 0.0)
        local_reasons = set(local_result.get("reasons") or [])
        label = (classification or {}).get("label")
        class_score = float((classification or {}).get("score") or 0.0)

        if local_score >= settings.AI_MIN_LOCAL_SCORE:
            return True, "eligible_local_score"
        if {"contains_url", "telegram_bot_reference", "bot_with_paid_service"} & local_reasons and local_score >= 0.25:
            return True, "eligible_link_or_bot"
        if label in {"scam", "phishing", "spam"} and class_score >= 0.5:
            return True, "eligible_classifier"
        if repetition_score >= 0.5:
            return True, "eligible_repetition"
        if graph_score >= 0.35:
            return True, "eligible_graph"

        return False, "skipped_low_risk"

    async def get_cached_analysis(self, session: AsyncSession, text_hash: str) -> AIMessageAnalysis | None:
        if not text_hash:
            return None
        result = await session.execute(
            select(AIMessageAnalysis)
            .where(
                AIMessageAnalysis.text_hash == text_hash,
                or_(
                    AIMessageAnalysis.status.in_(["analyzed", "cached"]),
                    AIMessageAnalysis.status.is_(None),
                ),
            )
            .order_by(AIMessageAnalysis.created_at.desc())
        )
        return result.scalars().first()


ai_rate_limiter = AIRateLimiter()
ai_eligibility_policy = AIEligibilityPolicy()
