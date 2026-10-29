from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from config.settings import settings
from ai.prompts import ANTI_SCAM_SYSTEM_PROMPT, build_user_prompt
from ai.schemas import fallback_ai_result

logger = logging.getLogger(__name__)


class GroqAIClient:
    def __init__(self):
        self.provider = "groq"
        self.model = settings.GROQ_MODEL
        self.timeout = settings.GROQ_TIMEOUT
        self.max_chars = 6000

    @property
    def is_configured(self) -> bool:
        return bool(settings.GROQ_API_KEY)

    async def analyze_message(self, text: str, context: dict | None = None) -> dict[str, Any]:
        if not self.is_configured:
            return fallback_ai_result(
                provider=self.provider,
                model=self.model,
                reason="GROQ_API_KEY is not configured",
            )

        prompt = build_user_prompt((text or "")[: self.max_chars], context)
        for attempt in range(2):
            try:
                return await asyncio.wait_for(
                    asyncio.to_thread(self._create_completion, prompt),
                    timeout=self.timeout,
                )
            except Exception as exc:
                if attempt == 0:
                    logger.warning("Groq analysis failed, retrying once: %s", exc)
                    await asyncio.sleep(0.5)
                    continue
                logger.error("Groq analysis failed: %s", exc)
                return fallback_ai_result(
                    provider=self.provider,
                    model=self.model,
                    reason="Groq API unavailable",
                )

        return fallback_ai_result(provider=self.provider, model=self.model)

    def _create_completion(self, prompt: str) -> dict[str, Any]:
        try:
            from groq import Groq
        except ImportError as exc:
            raise RuntimeError("groq package is not installed") from exc

        client = Groq(api_key=settings.GROQ_API_KEY, timeout=self.timeout)
        response = client.chat.completions.create(
            model=self.model,
            temperature=settings.GROQ_TEMPERATURE,
            max_tokens=settings.GROQ_MAX_TOKENS,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": ANTI_SCAM_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)
        parsed["provider"] = self.provider
        parsed["model"] = self.model
        parsed["raw_response"] = parsed.copy()
        return parsed


groq_ai_client = GroqAIClient()
