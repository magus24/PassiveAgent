import logging

logger = logging.getLogger(__name__)


class RiskEngineV2:
    """Multi-factor threat detection risk scoring engine.

    The project stores final Message.risk_score as 0.0-1.0 for backwards
    compatibility with existing dashboard and alert thresholds. Groq returns
    ai_score as 0-100 and is normalized before merging.
    """

    HIGH_THRESHOLD = 0.7
    MEDIUM_THRESHOLD = 0.4

    WEIGHTS = {
        "base_pattern": 0.35,
        "behavior": 0.20,
        "semantic": 0.15,
        "graph": 0.15,
        "ai": 0.15,
    }

    def calculate_score(
        self,
        classification: dict | None,
        links: list[str],
        repetition_score: float,
        behavior_score: float,
        patterns_found: list[str],
        local_score: float | None = None,
        local_category: str | None = None,
        local_reasons: list[str] | None = None,
        ai_score: float | None = None,
        ai_label: str | None = None,
        ai_risk_level: str | None = None,
        ai_confidence: float | None = None,
        graph_score: float | None = None,
    ) -> tuple[float, str, list[str]]:
        reasons = []

        base_pattern_score = self._calculate_base_pattern_score(
            classification,
            links,
            patterns_found,
            reasons,
        )
        if local_score is not None:
            base_pattern_score = max(base_pattern_score, max(0.0, min(1.0, local_score)))
            if local_category and local_category != "normal":
                reasons.append(f"Local rules classified as {local_category} ({local_score:.2f})")
            for reason in local_reasons or []:
                if reason not in reasons:
                    reasons.append(reason)

        semantic_score = max(0.0, min(1.0, repetition_score or 0.0))
        if semantic_score > 0:
            reasons.append("High semantic similarity to past messages")

        normalized_behavior = max(0.0, min(1.0, behavior_score or 0.0))
        if normalized_behavior > 0.5:
            reasons.append("Suspicious sender behavior (high frequency / spam network)")

        normalized_graph = max(0.0, min(1.0, graph_score or 0.0))
        if normalized_graph > 0:
            reasons.append(f"Graph intelligence risk signal ({normalized_graph:.2f})")

        normalized_ai = None
        if ai_score is not None and ai_confidence is not None and ai_confidence > 0:
            normalized_ai = max(0.0, min(1.0, ai_score / 100.0))
            if ai_label and ai_label != "normal":
                reasons.append(
                    f"Groq AI detected {ai_label} ({ai_score:.0f}/100, confidence {ai_confidence:.2f})"
                )

        weighted_signals = {
            "base_pattern": base_pattern_score,
            "behavior": normalized_behavior,
            "semantic": semantic_score,
            "graph": normalized_graph,
        }
        if normalized_ai is not None:
            weighted_signals["ai"] = normalized_ai

        total_weight = sum(self.WEIGHTS[name] for name in weighted_signals)
        total_score = sum(
            weighted_signals[name] * self.WEIGHTS[name]
            for name in weighted_signals
        ) / max(total_weight, 0.0001)

        if ai_risk_level == "critical" or (
            normalized_ai is not None and normalized_ai >= 0.9 and (ai_confidence or 0) >= 0.7
        ):
            total_score = max(total_score, 0.85)

        total_score = round(max(0.0, min(1.0, total_score)), 4)
        if local_score is not None and local_category and local_category != "normal":
            total_score = max(total_score, round(max(0.0, min(1.0, local_score)), 4))
        if local_category in {"service_ad", "suspicious"} and total_score >= 0.35:
            total_score = max(total_score, 0.4)
        if local_category in {"scam", "phishing"} and total_score >= 0.45:
            total_score = max(total_score, 0.7)
        level = self._risk_level(total_score)
        return total_score, level, reasons

    def _calculate_base_pattern_score(
        self,
        classification: dict | None,
        links: list[str],
        patterns_found: list[str],
        reasons: list[str],
    ) -> float:
        ml_score = 0.0
        if classification and classification.get("label") != "normal":
            label = classification.get("label", "")
            base_score = classification.get("score", 0.0)
            if label in ["scam", "phishing"]:
                ml_score = base_score
                reasons.append(f"ML classifier detected {label} ({base_score:.2f})")
            elif label == "spam":
                ml_score = base_score * 0.7
                reasons.append(f"ML classifier detected spam ({base_score:.2f})")

        link_score = 0.0
        if links:
            if len(links) > 2:
                link_score += 0.5
                reasons.append(f"High number of links ({len(links)})")

            suspicious_tlds = [".xyz", ".top", ".click", ".work", ".buzz"]
            shorteners = ["bit.ly", "tinyurl", "t.co", "is.gd", "cutt.ly"]
            for link in links:
                link_lower = link.lower()
                if any(tld in link_lower for tld in suspicious_tlds):
                    link_score += 0.5
                    reasons.append("Suspicious TLD in link")
                    break
                if any(short in link_lower for short in shorteners):
                    link_score += 0.3
                    reasons.append("URL shortener used")
                    break
                if "t.me/+" in link_lower or "t.me/joinchat" in link_lower:
                    link_score += 0.4
                    reasons.append("Contains Telegram invite link")
                    break

            if link_score == 0:
                link_score = 0.2

        pattern_score = 0.0
        if patterns_found:
            pattern_score = min(1.0, len(patterns_found) * 0.5)
            reasons.append(f"Known threat patterns detected: {', '.join(patterns_found)}")

        return max(ml_score, min(1.0, link_score), pattern_score)

    def _risk_level(self, score: float) -> str:
        if score >= self.HIGH_THRESHOLD:
            return "HIGH"
        if score >= self.MEDIUM_THRESHOLD:
            return "MEDIUM"
        return "LOW"


risk_engine_v2 = RiskEngineV2()
