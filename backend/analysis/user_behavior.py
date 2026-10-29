import time
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class UserBehaviorEngine:
    def __init__(self):
        # Track per-user behavior in memory (could be moved to Redis for production)
        # user_id -> { "timestamps": [float], "chats": set[str], "link_count": int, "total_messages": int }
        self.user_stats = defaultdict(lambda: {
            "timestamps": [],
            "chats": set(),
            "link_count": 0,
            "total_messages": 0
        })
        self.WINDOW_SECONDS = 60 # 1 minute window for frequency

    def update_and_evaluate(self, user_id: str, chat_id: str, has_link: bool) -> float:
        """Updates user behavior metrics and returns a behavior score (0-1)."""
        if not user_id:
            return 0.0

        now = time.time()
        stats = self.user_stats[user_id]
        
        # Update metrics
        stats["timestamps"].append(now)
        stats["chats"].add(chat_id)
        stats["total_messages"] += 1
        if has_link:
            stats["link_count"] += 1
            
        # Prune old timestamps
        cutoff = now - self.WINDOW_SECONDS
        stats["timestamps"] = [ts for ts in stats["timestamps"] if ts > cutoff]
        
        # Calculate behavioral signals
        msg_per_min = len(stats["timestamps"])
        chat_count = len(stats["chats"])
        link_ratio = stats["link_count"] / max(1, stats["total_messages"])
        
        score = 0.0
        
        # High message frequency -> bot suspicion
        if msg_per_min > 10:
            score += 0.6
        elif msg_per_min > 5:
            score += 0.3
            
        # Many chats + high link ratio -> spam network / phishing
        if chat_count > 3 and link_ratio > 0.5:
            score += 0.4
            
        return min(1.0, score)

user_behavior_engine = UserBehaviorEngine()
