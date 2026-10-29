import logging
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from storage.db import Message

logger = logging.getLogger(__name__)

class SemanticMatcher:
    async def find_repeats(self, session: AsyncSession, embedding: list[float], user_id: int | None, chat_id: int | None) -> float:
        """
        Check if the current embedding is similar to recent messages.
        Returns a repetition score (0.0 to 1.0).
        """
        if not embedding:
            return 0.0
            
        try:
            # Look for similar messages in the database (cosine distance < 0.15 is similarity > 0.85)
            # We use pgvector's cosine_distance. The smaller the distance, the more similar.
            distance_threshold = 0.15
            
            query = (
                select(Message)
                .filter(Message.embedding.isnot(None))
                .filter(Message.embedding.cosine_distance(embedding) < distance_threshold)
                .order_by(Message.embedding.cosine_distance(embedding))
                .limit(5)
            )
            
            result = await session.execute(query)
            similar_msgs = result.scalars().all()
            
            if not similar_msgs:
                return 0.0
                
            score = 0.5 # Base score for having any highly similar message
            for msg in similar_msgs:
                # Same message in multiple chats
                if msg.chat_id != chat_id:
                    score += 0.5
                # Same user repeats message
                if msg.user_id == user_id:
                    score += 0.3
                    
            return min(1.0, score)
        except Exception as e:
            logger.error(f"Semantic matching failed: {e}")
            return 0.0

semantic_matcher = SemanticMatcher()
