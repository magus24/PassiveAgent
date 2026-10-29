import re
import logging

logger = logging.getLogger(__name__)


class NLPEngine:
    """Multilingual keyword and entity detection engine.

    Supports English, Russian, and Uzbek (Latin + Cyrillic).
    Uses regex-based entity extraction for OSINT-relevant patterns
    (crypto wallets, phone numbers, emails, card numbers).
    """

    def __init__(self):
        # Suspicious keywords — EN / RU / UZ
        self.suspicious_keywords = [
            # English
            "scam", "phishing", "crypto", "investment", "guaranteed",
            "giveaway", "free money", "hack", "dump", "pump",
            "wallet", "airdrop", "profit", "earn fast", "double your",
            # Russian
            "мошенничество", "фишинг", "скам", "крипта", "инвестиции",
            "гарантированный", "бесплатные деньги", "заработок", "вложения",
            "розыгрыш", "хакер", "взлом", "обман", "развод", "лохотрон",
            "перевод на карту", "выигрыш", "приз", "кошелёк", "кошелек",
            "пирамида", "схема заработка", "пассивный доход",
            # Uzbek (Latin)
            "firibgarlik", "aldash", "pul ishlash", "kripto", "investitsiya",
            "kafolatlangan", "bepul pul", "xakerlik", "hiyla",
            "yutuq", "sovrin", "daromad", "tez pul", "hamyon",
            # Uzbek (Cyrillic)
            "фирибгарлик", "алдаш", "пул ишлаш", "крипто", "инвестиция",
            "кафолатланган", "бепул пул", "хакерлик", "ҳийла",
            "ютуқ", "совриқ", "даромад", "тез пул", "ҳамён",
        ]

        # OSINT entity patterns
        self._patterns = {
            "crypto_wallet": re.compile(
                r'\b(?:'
                r'(?:0x[a-fA-F0-9]{40})'                   # ETH
                r'|(?:[13][a-km-zA-HJ-NP-Z1-9]{25,34})'   # BTC
                r'|(?:T[a-zA-Z0-9]{33})'                   # TRX/TRON
                r')\b'
            ),
            "phone": re.compile(
                r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{2,4}[-.\s]?\d{2,6}'
            ),
            "email": re.compile(
                r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            ),
            "card_number": re.compile(
                r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
            ),
        }

    def analyze_text(self, text: str) -> dict:
        """Analyze text for suspicious keywords and OSINT-relevant entities.

        Args:
            text: Input text (any language).

        Returns:
            Dict with keys:
                - keywords_found: list[str] — matched suspicious keywords
                - entities: list[dict] — extracted entities with type and value
        """
        results = {
            "keywords_found": [],
            "entities": [],
        }

        if not text:
            return results

        lower_text = text.lower()

        # Keyword matching (language-agnostic — works on lowercased text)
        for keyword in self.suspicious_keywords:
            if keyword in lower_text:
                results["keywords_found"].append(keyword)

        # Regex entity extraction (OSINT-relevant patterns)
        for entity_type, pattern in self._patterns.items():
            for match in pattern.finditer(text):
                results["entities"].append({
                    "text": match.group(),
                    "label": entity_type,
                })

        return results


nlp_engine = NLPEngine()
