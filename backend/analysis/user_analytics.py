import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from storage.db import Message, UserStat
from collections import Counter
import re

logger = logging.getLogger(__name__)

async def update_user_stats(user_id: int, session: AsyncSession):
    """Recalculate and update the user_stats table for a given user."""
    try:
        # Get total messages
        total_msgs_result = await session.execute(
            select(func.count(Message.id)).where(Message.user_id == user_id)
        )
        total_msgs = total_msgs_result.scalar() or 0

        if total_msgs == 0:
            return

        # Get total distinct chats
        chats_result = await session.execute(
            select(func.count(func.distinct(Message.chat_id)))
            .where(Message.user_id == user_id, Message.chat_id.isnot(None))
        )
        total_chats = chats_result.scalar() or 0

        # Get favorite chat
        fav_chat_result = await session.execute(
            select(Message.chat_id, func.count(Message.id).label('msg_count'))
            .where(Message.user_id == user_id, Message.chat_id.isnot(None))
            .group_by(Message.chat_id)
            .order_by(func.count(Message.id).desc())
            .limit(1)
        )
        fav_chat_row = fav_chat_result.first()
        favorite_chat = str(fav_chat_row[0]) if fav_chat_row else None

        # Get media percent
        media_msgs_result = await session.execute(
            select(func.count(Message.id))
            .where(Message.user_id == user_id, Message.has_media == True)
        )
        media_msgs = media_msgs_result.scalar() or 0
        media_percent = (media_msgs / total_msgs) * 100.0 if total_msgs > 0 else 0.0

        # Get reply percent
        reply_msgs_result = await session.execute(
            select(func.count(Message.id))
            .where(Message.user_id == user_id, Message.is_reply == True)
        )
        reply_msgs = reply_msgs_result.scalar() or 0
        reply_percent = (reply_msgs / total_msgs) * 100.0 if total_msgs > 0 else 0.0

        # Upsert UserStat
        stat_result = await session.execute(
            select(UserStat).where(UserStat.user_id == user_id)
        )
        stat = stat_result.scalar_one_or_none()

        if stat is None:
            stat = UserStat(user_id=user_id)
            session.add(stat)

        stat.total_messages = total_msgs
        stat.total_chats = total_chats
        stat.media_percent = media_percent
        stat.reply_percent = reply_percent
        stat.favorite_chat = favorite_chat

        # Note: We rely on the caller to commit() the session
    except Exception as e:
        logger.error(f"Failed to update user stats for {user_id}: {e}")

async def get_user_analytics(user_id: int, session: AsyncSession):
    """Retrieve full analytics for a user including distribution and word frequency."""
    try:
        # Message distribution by type
        type_dist_result = await session.execute(
            select(Message.message_type, func.count(Message.id))
            .where(Message.user_id == user_id)
            .group_by(Message.message_type)
        )
        message_distribution = {row[0]: row[1] for row in type_dist_result.all()}

        # Top chats
        top_chats_result = await session.execute(
            select(Message.chat_id, func.count(Message.id))
            .where(Message.user_id == user_id, Message.chat_id.isnot(None))
            .group_by(Message.chat_id)
            .order_by(func.count(Message.id).desc())
            .limit(5)
        )
        top_chats = [{"chat_id": str(row[0]), "count": row[1]} for row in top_chats_result.all()]

        # Basic word frequency (last 100 messages to avoid heavy computation)
        msgs_result = await session.execute(
            select(Message.text)
            .where(Message.user_id == user_id, Message.text != None, Message.text != "")
            .order_by(Message.timestamp.desc())
            .limit(100)
        )
        all_text = " ".join([row[0] for row in msgs_result.all()])
        words = re.findall(r'\b\w+\b', all_text.lower())
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'it', 'that', 'this', 'i', 'you', 'he', 'she', 'we', 'they'}
        filtered_words = [w for w in words if w not in stop_words and len(w) > 2]
        word_freq = dict(Counter(filtered_words).most_common(20))

        # Get base stats
        stat_result = await session.execute(
            select(UserStat).where(UserStat.user_id == user_id)
        )
        stat = stat_result.scalar_one_or_none()

        return {
            "message_distribution": message_distribution,
            "media_percent": stat.media_percent if stat else 0.0,
            "reply_percent": stat.reply_percent if stat else 0.0,
            "top_chats": top_chats,
            "word_frequency": word_freq
        }
    except Exception as e:
        logger.error(f"Failed to get analytics for {user_id}: {e}")
        return {}
