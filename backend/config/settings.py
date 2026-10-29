import os
from pathlib import Path
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

class Settings:
    # Telegram
    TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
    TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
    TELEGRAM_PHONE_NUMBER = os.getenv("TELEGRAM_PHONE_NUMBER")

    # PostgreSQL
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "passiveagent")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
    DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

    # Neo4j
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

    # SpiderFoot
    SPIDERFOOT_HOST = os.getenv("SPIDERFOOT_HOST", "127.0.0.1")
    SPIDERFOOT_PORT = os.getenv("SPIDERFOOT_PORT", "5001")

    # API
    API_HOST = os.getenv("API_HOST", "127.0.0.1")
    API_PORT = int(os.getenv("API_PORT", "18080"))

    # AI provider
    AI_PROVIDER = os.getenv("AI_PROVIDER", "groq")
    AI_ENABLED = os.getenv("AI_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GROQ_TEMPERATURE = float(os.getenv("GROQ_TEMPERATURE", "0.2"))
    GROQ_MAX_TOKENS = int(os.getenv("GROQ_MAX_TOKENS", "800"))
    GROQ_TIMEOUT = float(os.getenv("GROQ_TIMEOUT", "30"))
    AI_DAILY_LIMIT = int(os.getenv("AI_DAILY_LIMIT", "300"))
    AI_PER_MINUTE_LIMIT = int(os.getenv("AI_PER_MINUTE_LIMIT", "5"))
    AI_MIN_LOCAL_SCORE = float(os.getenv("AI_MIN_LOCAL_SCORE", "0.35"))
    AI_ANALYZE_ONLY_CANDIDATES = os.getenv("AI_ANALYZE_ONLY_CANDIDATES", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

settings = Settings()
