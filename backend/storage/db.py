import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config.settings import settings

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class UserNameHistory(Base):
    __tablename__ = "user_names_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), index=True)
    name = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class UserStat(Base):
    __tablename__ = "user_stats"

    user_id = Column(BigInteger, ForeignKey("users.id"), primary_key=True)
    total_messages = Column(Integer, default=0)
    total_chats = Column(Integer, default=0)
    media_percent = Column(Float, default=0.0)
    reply_percent = Column(Float, default=0.0)
    favorite_chat = Column(String, nullable=True)
    risk_score = Column(Float, default=0.0)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), index=True, nullable=True)
    chat_id = Column(BigInteger, index=True, nullable=True)
    channel_id = Column(String, index=True)
    sender_id = Column(String, index=True)
    text = Column(Text)
    message_type = Column(String, default="text")
    has_media = Column(Boolean, default=False)
    has_link = Column(Boolean, default=False)
    is_reply = Column(Boolean, default=False)
    links = Column(Text)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    risk_score = Column(Float, default=0.0)
    risk_level = Column(String, default="LOW")
    reasons = Column(JSON, nullable=True)
    embedding = Column(Vector(384), nullable=True)
    classification_label = Column(String, nullable=True)
    classification_score = Column(Float, nullable=True)
    local_score = Column(Float, nullable=True)
    local_category = Column(String, nullable=True)
    local_reasons = Column(JSON, nullable=True)
    text_hash = Column(String, index=True, nullable=True)
    extracted_entities = Column(JSON, nullable=True)
    campaign_key = Column(String, index=True, nullable=True)
    review_status = Column(String, default="new", index=True)
    review_note = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    ai_analysis = Column(JSON, nullable=True)
    ai_score = Column(Float, nullable=True)
    ai_label = Column(String, nullable=True)
    ai_status = Column(String, default="not_evaluated", index=True)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    message_telegram_id = Column(Integer, index=True)
    channel_id = Column(String, index=True)
    sender_id = Column(String, index=True)
    text_preview = Column(Text)
    risk_score = Column(Float)
    risk_level = Column(String)
    classification_label = Column(String, nullable=True)
    classification_score = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    resolved = Column(Boolean, default=False)


class AIMessageAnalysis(Base):
    __tablename__ = "ai_message_analysis"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), index=True, nullable=False)
    provider = Column(String, default="groq")
    model = Column(String, nullable=True)
    label = Column(String, nullable=True)
    risk_level = Column(String, nullable=True)
    risk_score = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    summary = Column(Text, nullable=True)
    reasons = Column(JSON, nullable=True)
    detected_patterns = Column(JSON, nullable=True)
    recommended_action = Column(String, nullable=True)
    raw_response = Column(JSON, nullable=True)
    text_hash = Column(String, index=True, nullable=True)
    status = Column(String, default="analyzed", index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS ai_analysis JSON"))
        await conn.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS ai_score FLOAT"))
        await conn.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS ai_label VARCHAR"))
        await conn.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS ai_status VARCHAR"))
        await conn.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS local_score FLOAT"))
        await conn.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS local_category VARCHAR"))
        await conn.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS local_reasons JSON"))
        await conn.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS text_hash VARCHAR"))
        await conn.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS extracted_entities JSON"))
        await conn.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS campaign_key VARCHAR"))
        await conn.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS review_status VARCHAR DEFAULT 'new'"))
        await conn.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS review_note TEXT"))
        await conn.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP"))
        await conn.execute(text("ALTER TABLE ai_message_analysis ADD COLUMN IF NOT EXISTS text_hash VARCHAR"))
        await conn.execute(text("ALTER TABLE ai_message_analysis ADD COLUMN IF NOT EXISTS status VARCHAR"))


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
