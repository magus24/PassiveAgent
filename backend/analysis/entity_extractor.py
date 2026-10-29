import hashlib
import re
from urllib.parse import urlparse


class EntityExtractor:
    URL_RE = re.compile(r"https?://[^\s<>\"']+|www\.[^\s<>\"']+", re.IGNORECASE)
    USERNAME_RE = re.compile(r"@[a-zA-Z0-9_]{4,}", re.IGNORECASE)
    PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")
    CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
    CRYPTO_WALLET_RE = re.compile(
        r"\b(?:0x[a-fA-F0-9]{40}|[13][a-km-zA-HJ-NP-Z1-9]{25,34}|[A-Z0-9]{48})\b"
    )

    def extract(self, text: str, links: list[str] | None = None) -> dict:
        text = text or ""
        urls = self._unique(links or self.URL_RE.findall(text))
        usernames = self._unique(self.USERNAME_RE.findall(text))
        bots = [name for name in usernames if name.lower().endswith("bot")]
        phones = self._unique([self._clean_phone(value) for value in self.PHONE_RE.findall(text)])
        bank_cards = self._unique([self._clean_digits(value) for value in self.CARD_RE.findall(text)])
        crypto_wallets = self._unique(self.CRYPTO_WALLET_RE.findall(text))

        return {
            "urls": urls,
            "domains": self._unique([self._domain(url) for url in urls if self._domain(url)]),
            "usernames": usernames,
            "bots": bots,
            "phones": phones,
            "bank_cards": bank_cards,
            "crypto_wallets": crypto_wallets,
        }

    def campaign_key(self, text_hash: str, entities: dict) -> str:
        for field in ("bots", "domains", "phones", "crypto_wallets", "bank_cards"):
            values = entities.get(field) or []
            if values:
                return f"{field}:{values[0].lower()}"
        return f"text:{text_hash[:16]}" if text_hash else ""

    def _domain(self, url: str) -> str:
        value = url if "://" in url else f"https://{url}"
        parsed = urlparse(value)
        return (parsed.netloc or "").lower().strip("/")

    def _clean_phone(self, value: str) -> str:
        return re.sub(r"[^\d+]", "", value)

    def _clean_digits(self, value: str) -> str:
        return re.sub(r"\D", "", value)

    def _unique(self, values: list[str]) -> list[str]:
        seen = set()
        result = []
        for value in values:
            if not value:
                continue
            key = value.lower()
            if key in seen:
                continue
            seen.add(key)
            result.append(value)
        return result


entity_extractor = EntityExtractor()
