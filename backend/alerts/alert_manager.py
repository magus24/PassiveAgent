import logging
from storage.db import Alert, async_session

logger = logging.getLogger(__name__)


class AlertManager:
    """Manages alert creation, persistence, and notification.

    Alerts are triggered when a message reaches HIGH risk level.
    They are persisted in PostgreSQL via the Alert model and
    logged to the console.
    """

    async def trigger_alert(
        self,
        message_data: dict,
        risk_score: float,
        risk_level: str,
        classification_label: str | None = None,
        classification_score: float | None = None,
    ):
        """Evaluate and persist an alert if risk level is HIGH.

        Args:
            message_data: Dict with keys: id, sender_id, channel_id, text, links
            risk_score: Numeric risk score 0–1
            risk_level: "LOW" | "MEDIUM" | "HIGH"
            classification_label: ML classification result
            classification_score: ML confidence 0–1
        """
        if risk_level != "HIGH":
            return

        # Console logging (preserved from MVP)
        logger.warning(f"🚨 HIGH RISK ALERT! Score: {risk_score}")
        logger.warning(
            f"Message ID: {message_data.get('id')} "
            f"from Sender: {message_data.get('sender_id')}"
        )
        logger.warning(f"Classification: {classification_label} ({classification_score})")
        logger.warning(f"Text: {message_data.get('text')}")
        logger.warning(f"Links: {message_data.get('links')}")

        # Persist to PostgreSQL
        try:
            async with async_session() as session:
                alert = Alert(
                    message_telegram_id=message_data.get("id"),
                    channel_id=message_data.get("channel_id"),
                    sender_id=message_data.get("sender_id"),
                    text_preview=(message_data.get("text") or "")[:500],
                    risk_score=risk_score,
                    risk_level=risk_level,
                    classification_label=classification_label,
                    classification_score=classification_score,
                )
                session.add(alert)
                await session.commit()
                logger.info(f"Alert persisted for message {message_data.get('id')}")
        except Exception as e:
            logger.error(f"Failed to persist alert: {e}")


alert_manager = AlertManager()
