from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator


Label = Literal["scam", "phishing", "spam", "suspicious", "normal"]
RiskLevel = Literal["low", "medium", "high", "critical"]
RecommendedAction = Literal["ignore", "monitor", "create_alert", "block_or_report"]


class ExtractedEntities(BaseModel):
    phones: list[str] = Field(default_factory=list)
    usernames: list[str] = Field(default_factory=list)
    urls: list[str] = Field(default_factory=list)
    crypto_wallets: list[str] = Field(default_factory=list)
    bank_cards: list[str] = Field(default_factory=list)


class AIAnalysisResult(BaseModel):
    label: Label = "normal"
    risk_level: RiskLevel = "low"
    risk_score: float = 0.0
    confidence: float = 0.0
    reasons: list[str] = Field(default_factory=list)
    detected_patterns: list[str] = Field(default_factory=list)
    summary: str = ""
    recommended_action: RecommendedAction = "ignore"
    language: str = "unknown"
    extracted_entities: ExtractedEntities = Field(default_factory=ExtractedEntities)
    provider: str = "groq"
    model: str = ""
    raw_response: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None

    @field_validator("risk_score", mode="before")
    @classmethod
    def normalize_risk_score(cls, value):
        try:
            score = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(100.0, score))

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, value):
        try:
            score = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, score))


def fallback_ai_result(
    *,
    provider: str = "groq",
    model: str = "",
    reason: str = "AI analysis unavailable",
) -> dict[str, Any]:
    return AIAnalysisResult(
        provider=provider,
        model=model,
        error=reason,
        summary=reason,
    ).model_dump()
