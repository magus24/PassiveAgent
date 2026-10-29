import logging
from telethon import TelegramClient, events
from config.settings import settings
from processing.preprocess import preprocessor
from analysis.nlp_engine import nlp_engine
from analysis.risk_engine_v2 import risk_engine_v2
from analysis.embedding_engine import embedding_engine
from analysis.classifier import classifier
from analysis.patterns import pattern_detector
from analysis.user_behavior import user_behavior_engine
from analysis.semantic_matcher import semantic_matcher
from analysis.user_risk import user_risk_engine
from storage.db import Message, User, UserNameHistory, async_session
from graph.graph_builder import graph_builder
from alerts.alert_manager import alert_manager
from spiderfoot_service.runner import spiderfoot_runner
from analysis.user_analytics import update_user_stats
from analysis.entity_extractor import entity_extractor
from analysis.telegram_threat_patterns import telegram_threat_analyzer
from ai.ai_service import analyze_with_policy, build_ai_record
from sqlalchemy.future import select
import time


logger = logging.getLogger(__name__)


class TelegramCollector:
    def __init__(self):
        self.api_id = settings.TELEGRAM_API_ID
        self.api_hash = settings.TELEGRAM_API_HASH

        if not self.api_id or not self.api_hash:
            logger.warning(
                "TELEGRAM_API_ID or TELEGRAM_API_HASH not set. "
                "Telegram listener will not start."
            )
            self.client = None
        else:
            self.client = TelegramClient(
                'passive_agent_session', self.api_id, self.api_hash
            )

        # List of channels to monitor (could be loaded from DB)
        # Leave empty to listen to all joined dialogs for MVP
        self.target_channels = []

    async def start(self):
        if not self.client:
            return

        await self.client.start()
        logger.info("Telegram client started. Listening for messages...")

        @self.client.on(
            events.NewMessage(
                chats=self.target_channels if self.target_channels else None
            )
        )
        async def handler(event):
            try:
                await self.process_message(event)
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)

        # Run the client until disconnected
        await self.client.run_until_disconnected()

    async def process_message(self, event):
        """Full intelligence pipeline for each incoming message.

        Each stage is wrapped in try/except for fault tolerance:
        a failure in one stage (e.g., Neo4j down) does not prevent
        other stages (e.g., DB storage) from completing.
        """
        t_start = time.monotonic()
        message_text = event.raw_text
        sender_id = str(event.sender_id) if event.sender_id else "unknown"
        channel_id = str(event.chat_id) if event.chat_id else "unknown"
        
        # User details extraction
        sender = await event.get_sender()
        user_id = sender.id if sender and hasattr(sender, 'id') else None
        username = getattr(sender, 'username', None)
        first_name = getattr(sender, 'first_name', None)
        last_name = getattr(sender, 'last_name', None)

        # ── Stage 1: Preprocessing ──────────────────────────────────
        try:
            cleaned_text = preprocessor.clean_text(message_text)
            links = preprocessor.extract_urls(message_text)
        except Exception as e:
            logger.error(f"[PIPELINE] Preprocessing failed: {e}")
            cleaned_text = message_text
            links = []

        local_result = telegram_threat_analyzer.analyze(message_text, links)
        extracted_entities = entity_extractor.extract(message_text, links)
        campaign_key = entity_extractor.campaign_key(local_result.get("text_hash"), extracted_entities)

        # Message classification
        is_reply = bool(event.message.reply_to)
        has_media = bool(event.message.media)
        message_type = "text"
        has_link = len(links) > 0

        if event.message.voice:
            message_type = "voice"
        elif event.message.video:
            message_type = "video"
        elif event.message.photo:
            message_type = "image"
        elif getattr(event.message, 'gif', False) or (event.message.document and getattr(event.message.document, 'mime_type', '') == 'video/mp4'):
            message_type = "gif"
        elif event.message.sticker:
            message_type = "sticker"
        elif event.message.document:
            message_type = "file"
        elif has_link:
            message_type = "link"

        timestamp = event.message.date.replace(tzinfo=None) if event.message.date else None

        # ── Stage 2: NLP Analysis & Pattern Detection ───────────────────────────────────
        nlp_results = {"keywords_found": [], "entities": []}
        patterns_found = []
        try:
            nlp_results = nlp_engine.analyze_text(cleaned_text)
            patterns_found = pattern_detector.detect_patterns(cleaned_text)
        except Exception as e:
            logger.error(f"[PIPELINE] NLP/Pattern analysis failed: {e}")

        # ── Stage 3: Embedding Generation ───────────────────────────
        embedding = None
        try:
            embedding = embedding_engine.generate_embedding(cleaned_text)
        except Exception as e:
            logger.error(f"[PIPELINE] Embedding generation failed: {e}")
            
        # ── Stage 3.5: Semantic Matcher ──────────────────────────────
        repetition_score = 0.0
        try:
            async with async_session() as session:
                repetition_score = await semantic_matcher.find_repeats(session, embedding, user_id, event.chat_id)
        except Exception as e:
            logger.error(f"[PIPELINE] Semantic match failed: {e}")

        # ── Stage 4: ML Classification ──────────────────────────────
        classification = {"label": "unknown", "score": 0.0, "all_scores": {}}
        classification_label = "unknown"
        classification_score = 0.0
        try:
            classification = classifier.classify(cleaned_text)
            classification_label = classification["label"]
            classification_score = classification["score"]
        except Exception as e:
            logger.error(f"[PIPELINE] Classification failed: {e}")
            
        # ── Stage 4.5: Behavior Tracking ──────────────────────────────
        behavior_score = 0.0
        try:
            behavior_score = user_behavior_engine.update_and_evaluate(sender_id, channel_id, has_link)
        except Exception as e:
            logger.error(f"[PIPELINE] Behavior tracking failed: {e}")

        # ── Stage 5: Graph Construction (Neo4j) ────────────────────
        try:
            await graph_builder.add_message_data(sender_id, channel_id, links)
        except Exception as e:
            logger.error(f"[PIPELINE] Graph construction failed: {e}")

        # ── Stage 6: Graph-based risk score ─────────────────────────
        graph_score = 0.0
        try:
            graph_score = await graph_builder.get_graph_score(sender_id, links)
        except Exception as e:
            logger.error(f"[PIPELINE] Graph score failed: {e}")

        ai_result = None
        ai_status = "not_evaluated"
        try:
            async with async_session() as session:
                ai_result, ai_status = await analyze_with_policy(
                    session=session,
                    message_text=message_text,
                    text_hash=local_result.get("text_hash"),
                    local_result=local_result,
                    metadata={
                        "sender_id": sender_id,
                        "chat_id": event.chat_id,
                        "channel_id": channel_id,
                        "urls": links,
                        "message_type": message_type,
                        "classification": classification,
                        "local_result": local_result,
                        "repetition_score": repetition_score,
                        "behavior_score": behavior_score,
                        "graph_score": graph_score,
                        "patterns_found": patterns_found,
                    },
                    classification=classification,
                    repetition_score=repetition_score,
                    graph_score=graph_score,
                )
        except Exception as e:
            logger.error(f"[PIPELINE] AI analysis failed: {e}")
            ai_status = "failed"

        # ── Stage 7: Multi-factor Risk Scoring (V2) ──────────────────────
        risk_score = 0.0
        risk_level = "LOW"
        reasons = []
        try:
            risk_score, risk_level, reasons = risk_engine_v2.calculate_score(
                classification=classification,
                links=links,
                repetition_score=repetition_score,
                behavior_score=behavior_score,
                patterns_found=patterns_found,
                local_score=local_result.get("local_score"),
                local_category=local_result.get("category"),
                local_reasons=local_result.get("reasons"),
                ai_score=ai_result.get("risk_score") if ai_result else None,
                ai_label=ai_result.get("label") if ai_result else None,
                ai_risk_level=ai_result.get("risk_level") if ai_result else None,
                ai_confidence=ai_result.get("confidence") if ai_result else None,
                graph_score=graph_score,
            )
        except Exception as e:
            logger.error(f"[PIPELINE] Risk scoring failed: {e}")

        review_status = "needs_review" if risk_score >= 0.4 else "new"

        t_pipeline = time.monotonic() - t_start
        logger.info(
            f"[{channel_id}] sender={sender_id} "
            f"class={classification_label}({classification_score:.2f}) "
            f"risk={risk_score:.4f}({risk_level}) "
            f"links={len(links)} text_len={len(message_text)} "
            f"pipeline_ms={t_pipeline*1000:.0f}"
        )

        msg_data = {
            "id": event.id,
            "sender_id": sender_id,
            "channel_id": channel_id,
            "text": message_text,
            "links": links,
        }

        # ── Stage 8: Alert Triggering ───────────────────────────────
        try:
            await alert_manager.trigger_alert(
                msg_data, risk_score, risk_level,
                classification_label=classification_label,
                classification_score=classification_score,
            )
        except Exception as e:
            logger.error(f"[PIPELINE] Alert triggering failed: {e}")

        # ── Stage 9: Database Storage (PostgreSQL) ──────────────────
        try:
            async with async_session() as session:
                # Upsert User
                if user_id:
                    user_result = await session.execute(select(User).where(User.id == user_id))
                    user = user_result.scalar_one_or_none()
                    current_name = f"{first_name or ''} {last_name or ''}".strip() or username or "unknown"
                    
                    if user is None:
                        user = User(id=user_id, username=username, first_name=first_name, last_name=last_name)
                        session.add(user)
                        # Add initial name history
                        session.add(UserNameHistory(user_id=user_id, name=current_name))
                    else:
                        # Check name change
                        old_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.username or "unknown"
                        if old_name != current_name:
                            session.add(UserNameHistory(user_id=user_id, name=current_name))
                        
                        user.username = username
                        user.first_name = first_name
                        user.last_name = last_name

                new_msg = Message(
                    telegram_id=event.id,
                    user_id=user_id,
                    chat_id=event.chat_id,
                    channel_id=channel_id,
                    sender_id=sender_id,
                    text=message_text,
                    message_type=message_type,
                    has_media=has_media,
                    has_link=has_link,
                    is_reply=is_reply,
                    links=",".join(links) if links else "",
                    timestamp=timestamp,
                    risk_score=risk_score,
                    risk_level=risk_level,
                    reasons=reasons,
                    embedding=embedding,
                    classification_label=classification_label,
                    classification_score=classification_score,
                    local_score=local_result.get("local_score"),
                    local_category=local_result.get("category"),
                    local_reasons=local_result.get("reasons"),
                    text_hash=local_result.get("text_hash"),
                    extracted_entities=extracted_entities,
                    campaign_key=campaign_key,
                    review_status=review_status,
                    ai_analysis=ai_result,
                    ai_score=ai_result.get("risk_score") if ai_result else None,
                    ai_label=ai_result.get("label") if ai_result else None,
                    ai_status=ai_status,
                )
                session.add(new_msg)
                await session.flush()

                if ai_result:
                    session.add(build_ai_record(
                        message_id=new_msg.id,
                        text_hash=local_result.get("text_hash"),
                        ai_result=ai_result,
                        status=ai_status,
                    ))
                await session.commit()

                # Update user stats
                if user_id:
                    await update_user_stats(user_id, session)
                    await session.commit()
        except Exception as e:
            logger.error(f"[PIPELINE] DB storage failed: {e}")

        # ── Stage 10: SpiderFoot OSINT Enrichment ───────────────────
        if risk_level == "HIGH":
            for link in links:
                try:
                    await spiderfoot_runner.trigger_scan(link)
                except Exception as e:
                    logger.error(f"[PIPELINE] SpiderFoot scan failed for {link}: {e}")


collector = TelegramCollector()
