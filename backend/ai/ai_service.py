from sqlalchemy.ext.asyncio import AsyncSession

from ai.ai_analyzer import ai_analyzer
from ai.ai_policy import ai_eligibility_policy, ai_rate_limiter
from storage.db import AIMessageAnalysis


def analysis_from_record(record: AIMessageAnalysis) -> dict:
    raw = record.raw_response or {}
    if raw:
        result = dict(raw)
    else:
        result = {
            "provider": record.provider,
            "model": record.model,
            "label": record.label,
            "risk_level": record.risk_level,
            "risk_score": record.risk_score,
            "confidence": record.confidence,
            "summary": record.summary,
            "reasons": record.reasons or [],
            "detected_patterns": record.detected_patterns or [],
            "recommended_action": record.recommended_action,
        }
    result["status"] = "cached"
    return result


async def analyze_with_policy(
    *,
    session: AsyncSession,
    message_text: str,
    text_hash: str,
    local_result: dict,
    metadata: dict,
    classification: dict | None = None,
    repetition_score: float = 0.0,
    graph_score: float = 0.0,
    force: bool = False,
) -> tuple[dict | None, str]:
    cached = await ai_eligibility_policy.get_cached_analysis(session, text_hash)
    if cached:
        return analysis_from_record(cached), "cached"

    should_analyze, reason = ai_eligibility_policy.should_analyze(
        text=message_text,
        local_result=local_result,
        classification=classification,
        repetition_score=repetition_score,
        graph_score=graph_score,
        force=force,
    )
    if not should_analyze:
        return None, reason

    allowed, limit_reason = await ai_rate_limiter.can_call(session)
    if not allowed:
        return None, limit_reason

    ai_rate_limiter.record_call()
    result = await ai_analyzer.analyze(message_text=message_text, metadata=metadata)
    if result.get("error"):
        return result, "failed"
    return result, "analyzed"


def build_ai_record(message_id: int, text_hash: str, ai_result: dict, status: str) -> AIMessageAnalysis:
    return AIMessageAnalysis(
        message_id=message_id,
        provider=ai_result.get("provider"),
        model=ai_result.get("model"),
        label=ai_result.get("label"),
        risk_level=ai_result.get("risk_level"),
        risk_score=ai_result.get("risk_score"),
        confidence=ai_result.get("confidence"),
        summary=ai_result.get("summary"),
        reasons=ai_result.get("reasons"),
        detected_patterns=ai_result.get("detected_patterns"),
        recommended_action=ai_result.get("recommended_action"),
        raw_response=ai_result,
        text_hash=text_hash,
        status=status,
    )
