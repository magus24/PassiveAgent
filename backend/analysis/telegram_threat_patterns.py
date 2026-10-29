import hashlib
import re
from dataclasses import dataclass, field


@dataclass
class LocalThreatResult:
    local_score: float = 0.0
    category: str = "normal"
    reasons: list[str] = field(default_factory=list)
    detected_patterns: list[str] = field(default_factory=list)
    text_hash: str = ""

    def as_dict(self) -> dict:
        return {
            "local_score": self.local_score,
            "category": self.category,
            "reasons": self.reasons,
            "detected_patterns": self.detected_patterns,
            "text_hash": self.text_hash,
        }


class TelegramThreatPatternAnalyzer:
    URL_RE = re.compile(r"https?://[^\s<>\"']+|www\.[^\s<>\"']+", re.IGNORECASE)
    BOT_RE = re.compile(r"@[a-zA-Z0-9_]*bot\b", re.IGNORECASE)
    USERNAME_RE = re.compile(r"@[a-zA-Z0-9_]{4,}", re.IGNORECASE)
    PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")
    CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
    CRYPTO_RE = re.compile(r"\b(?:ton|usdt|btc|eth|crypto|nft|wallet|hamyon|кошелек|крипто)\b", re.IGNORECASE)

    PATTERN_GROUPS = {
        "smm_service": {
            "score": 0.45,
            "category": "service_ad",
            "terms": [
                "nakrutka", "накрутка", "obunachi", "подписчик", "подписчики",
                "reaksiya", "реакция", "prosmotr", "просмотр", "smm",
                "kanal uchun", "kanalingiz", "telegram kanal", "avto xabar",
            ],
        },
        "telegram_paid_services": {
            "score": 0.45,
            "category": "suspicious",
            "terms": [
                "stars", "telegram premium", "premium", "virtual raqam",
                "виртуальный номер", "nomer sotiladi", "номер сотилади",
                "rus nomer", "raqamlar", "akkaunt", "аккаунт",
            ],
        },
        "financial": {
            "score": 0.50,
            "category": "suspicious",
            "terms": [
                "payme", "click", "karta", "карта", "limit", "лимит",
                "pul kerak", "qarz", "перевод", "оплата", "to'lov",
                "тулов", "деньги", "рубл", "so'm", "сум",
            ],
        },
        "urgency": {
            "score": 0.25,
            "category": "suspicious",
            "terms": [
                "srochna", "срочно", "tezkor", "быстро", "bugun",
                "сегодня", "hozir", "xozir", "завтра", "zavtra",
            ],
        },
        "giveaway_investment": {
            "score": 0.65,
            "category": "scam",
            "terms": [
                "giveaway", "розыгрыш", "invest", "инвестиция", "daromad",
                "заработок", "x2", "x3", "депозит", "деп", "bonus",
            ],
        },
        "phishing": {
            "score": 0.75,
            "category": "phishing",
            "terms": [
                "login", "verify", "подтверд", "tasdiq", "parol",
                "password", "код", "sms kod", "войти", "аккаунт блок",
            ],
        },
    }

    def analyze(self, text: str, links: list[str] | None = None) -> dict:
        normalized = self.normalize_text(text)
        result = LocalThreatResult(text_hash=self.text_hash(normalized))
        if not normalized or len(normalized) < 3:
            result.reasons.append("empty_or_too_short")
            return result.as_dict()

        urls = links if links is not None else self.URL_RE.findall(text or "")
        self._apply_keyword_patterns(normalized, result)
        self._apply_entity_patterns(text or "", normalized, urls, result)

        result.local_score = round(max(0.0, min(1.0, result.local_score)), 4)
        if result.local_score >= 0.7 and result.category in {"normal", "service_ad"}:
            result.category = "suspicious"
        elif result.local_score < 0.2 and result.category != "normal":
            result.category = "normal"
        return result.as_dict()

    def normalize_text(self, text: str) -> str:
        text = (text or "").lower()
        text = text.replace("ё", "е")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def text_hash(self, normalized_text: str) -> str:
        return hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()

    def _raise_score(self, result: LocalThreatResult, score: float, category: str, reason: str):
        if score > result.local_score:
            result.local_score = score
        if category != "normal" and (result.category == "normal" or score >= result.local_score):
            result.category = category
        if reason not in result.reasons:
            result.reasons.append(reason)
        if reason not in result.detected_patterns:
            result.detected_patterns.append(reason)

    def _apply_keyword_patterns(self, normalized: str, result: LocalThreatResult):
        for pattern_name, config in self.PATTERN_GROUPS.items():
            if any(term in normalized for term in config["terms"]):
                self._raise_score(
                    result,
                    config["score"],
                    config["category"],
                    pattern_name,
                )

    def _apply_entity_patterns(self, raw_text: str, normalized: str, urls: list[str], result: LocalThreatResult):
        if urls:
            self._raise_score(result, 0.25, "suspicious", "contains_url")
            if result.local_score >= 0.35:
                self._raise_score(result, min(0.8, result.local_score + 0.15), result.category, "url_with_risk_terms")

        if self.BOT_RE.search(raw_text):
            self._raise_score(result, 0.35, "service_ad", "telegram_bot_reference")
            if any(term in normalized for term in ["sot", "сот", "premium", "stars", "nakrutka", "obunachi"]):
                self._raise_score(result, 0.55, "suspicious", "bot_with_paid_service")
        elif self.USERNAME_RE.search(raw_text) and result.local_score >= 0.25:
            self._raise_score(result, result.local_score + 0.05, result.category, "telegram_username_reference")

        if self.PHONE_RE.search(raw_text) and any(term in normalized for term in ["ish", "работ", "oplata", "оплата"]):
            self._raise_score(result, 0.35, "suspicious", "job_or_payment_with_phone")

        if self.CARD_RE.search(raw_text):
            self._raise_score(result, 0.55, "suspicious", "bank_card_like_number")

        if self.CRYPTO_RE.search(normalized):
            self._raise_score(result, 0.45, "suspicious", "crypto_or_nft_reference")


telegram_threat_analyzer = TelegramThreatPatternAnalyzer()
