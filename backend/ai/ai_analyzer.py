from __future__ import annotations

import json
import logging
import re
from typing import Any

from config.settings import settings
from ai.groq_client import groq_ai_client
from ai.schemas import AIAnalysisResult, fallback_ai_result

logger = logging.getLogger(__name__)


class AIAntiScamAnalyzer:
    MIN_TEXT_LENGTH = 3

    async def analyze(self, message_text: str, metadata: dict | None = None) -> dict[str, Any]:
        if not settings.AI_ENABLED:
            return fallback_ai_result(
                provider=settings.AI_PROVIDER,
                model=settings.GROQ_MODEL,
                reason="AI analysis disabled",
            )

        if not message_text or len(message_text.strip()) < self.MIN_TEXT_LENGTH:
            return fallback_ai_result(
                provider=settings.AI_PROVIDER,
                model=settings.GROQ_MODEL,
                reason="Message text is too short for AI analysis",
            )

        if settings.AI_PROVIDER.lower() != "groq":
            return fallback_ai_result(
                provider=settings.AI_PROVIDER,
                model=settings.GROQ_MODEL,
                reason="Unsupported AI provider",
            )

        raw_result = await groq_ai_client.analyze_message(message_text, metadata)
        return self._normalize(raw_result)

    def _normalize(self, raw_result: dict | str | None) -> dict[str, Any]:
        parsed = self._coerce_json(raw_result)
        try:
            result = AIAnalysisResult(**parsed)
            return result.model_dump()
        except Exception as exc:
            logger.warning("AI JSON validation failed: %s", exc)
            fallback = fallback_ai_result(
                provider=settings.AI_PROVIDER,
                model=settings.GROQ_MODEL,
                reason="Invalid AI response",
            )
            fallback["raw_response"] = parsed if isinstance(parsed, dict) else {"value": parsed}
            return fallback

    def _coerce_json(self, value: dict | str | None) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        if not value:
            return {}
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                match = re.search(r"\{.*\}", value, re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group(0))
                    except json.JSONDecodeError:
                        return {}
        return {}


ai_analyzer = AIAntiScamAnalyzer()
