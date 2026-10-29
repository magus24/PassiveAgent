import unittest
import sys
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from api.main import app
from ai.ai_analyzer import AIAntiScamAnalyzer
from ai.ai_policy import AIEligibilityPolicy
from analysis.telegram_threat_patterns import telegram_threat_analyzer
from config.settings import settings


class AISmokeTests(unittest.IsolatedAsyncioTestCase):
    def test_ai_status_endpoint(self):
        client = TestClient(app)
        response = client.get("/ai/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("enabled", data)
        self.assertIn("provider", data)
        self.assertIn("model", data)
        self.assertIn("api_key_configured", data)
        self.assertNotIn("api_key", data)

    async def test_fallback_without_groq_api_key(self):
        original_key = settings.GROQ_API_KEY
        settings.GROQ_API_KEY = None
        try:
            result = await AIAntiScamAnalyzer().analyze(
                "Urgent payment required, click this link now",
                {"urls": ["https://example.com"]},
            )
        finally:
            settings.GROQ_API_KEY = original_key

        self.assertEqual(result["label"], "normal")
        self.assertEqual(result["risk_score"], 0.0)
        self.assertIn("error", result)

    def test_json_validation_normalizes_risk_score(self):
        analyzer = AIAntiScamAnalyzer()
        result = analyzer._normalize({
            "label": "phishing",
            "risk_level": "critical",
            "risk_score": 150,
            "confidence": 2,
            "reasons": ["credential collection"],
            "detected_patterns": ["phishing link"],
            "summary": "Suspicious login link.",
            "recommended_action": "block_or_report",
            "language": "en",
        })

        self.assertEqual(result["risk_score"], 100.0)
        self.assertEqual(result["confidence"], 1.0)

    def test_fallback_risk_score_range(self):
        result = AIAntiScamAnalyzer()._normalize({})
        self.assertGreaterEqual(result["risk_score"], 0.0)
        self.assertLessEqual(result["risk_score"], 100.0)

    def test_local_patterns_detect_service_ad(self):
        result = telegram_threat_analyzer.analyze(
            "Telegram kanal uchun 1000 ta reaksiya va obunachi kerakmi? @ric_smm_bot",
            [],
        )
        self.assertGreaterEqual(result["local_score"], 0.35)
        self.assertIn(result["category"], {"service_ad", "suspicious"})
        self.assertIn("telegram_bot_reference", result["reasons"])

    def test_ai_eligibility_skips_low_risk_text(self):
        result = telegram_threat_analyzer.analyze("Assalomu alaykum ishlar yaxshimi", [])
        allowed, reason = AIEligibilityPolicy().should_analyze(
            text="Assalomu alaykum ishlar yaxshimi",
            local_result=result,
            classification={"label": "normal", "score": 0.1},
        )
        self.assertFalse(allowed)
        self.assertEqual(reason, "skipped_low_risk")


if __name__ == "__main__":
    unittest.main()
