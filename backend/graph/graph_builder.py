from neo4j import GraphDatabase, AsyncGraphDatabase
import logging
from config.settings import settings

logger = logging.getLogger(__name__)

class GraphBuilder:
    def __init__(self):
        self.uri = settings.NEO4J_URI
        self.user = settings.NEO4J_USER
        self.password = settings.NEO4J_PASSWORD
        self.driver = AsyncGraphDatabase.driver(self.uri, auth=(self.user, self.password))

    async def close(self):
        await self.driver.close()

    async def add_message_data(self, sender_id: str, channel_id: str, links: list[str]):
        query = """
        MERGE (u:User {id: $sender_id})
        MERGE (c:Channel {id: $channel_id})
        MERGE (u)-[:POSTED_IN]->(c)
        """
        async with self.driver.session() as session:
            await session.run(query, sender_id=sender_id, channel_id=channel_id)
            
            for link in links:
                if link:
                    link_query = """
                    MATCH (u:User {id: $sender_id})
                    MATCH (c:Channel {id: $channel_id})
                    MERGE (l:Link {url: $link})
                    MERGE (u)-[:SHARED]->(l)
                    MERGE (l)-[:FOUND_IN]->(c)
                    """
                    await session.run(link_query, sender_id=sender_id, channel_id=channel_id, link=link)

    # ── Graph-based signal methods ──────────────────────────────────

    async def get_link_sharing_count(self, url: str) -> int:
        """How many distinct channels share this URL."""
        query = """
        MATCH (l:Link {url: $url})-[:FOUND_IN]->(c:Channel)
        RETURN count(DISTINCT c) AS channel_count
        """
        try:
            async with self.driver.session() as session:
                result = await session.run(query, url=url)
                record = await result.single()
                return record["channel_count"] if record else 0
        except Exception as e:
            logger.error(f"Graph query (link_sharing_count) failed: {e}")
            return 0

    async def get_user_channel_count(self, sender_id: str) -> int:
        """How many channels this user posts in."""
        query = """
        MATCH (u:User {id: $sender_id})-[:POSTED_IN]->(c:Channel)
        RETURN count(DISTINCT c) AS channel_count
        """
        try:
            async with self.driver.session() as session:
                result = await session.run(query, sender_id=sender_id)
                record = await result.single()
                return record["channel_count"] if record else 0
        except Exception as e:
            logger.error(f"Graph query (user_channel_count) failed: {e}")
            return 0

    async def get_link_user_count(self, url: str) -> int:
        """How many distinct users have shared this URL."""
        query = """
        MATCH (u:User)-[:SHARED]->(l:Link {url: $url})
        RETURN count(DISTINCT u) AS user_count
        """
        try:
            async with self.driver.session() as session:
                result = await session.run(query, url=url)
                record = await result.single()
                return record["user_count"] if record else 0
        except Exception as e:
            logger.error(f"Graph query (link_user_count) failed: {e}")
            return 0

    async def get_graph_score(self, sender_id: str, links: list[str]) -> float:
        """Compute a normalized graph-based risk score (0–1).
        
        Signals:
        - User posting in many channels (suspicious if > 5)
        - Links shared across multiple channels (suspicious if > 2)
        - Links shared by multiple users (coordinated behavior)
        """
        score = 0.0

        # Signal 1: User activity spread
        user_channels = await self.get_user_channel_count(sender_id)
        if user_channels > 10:
            score += 0.4
        elif user_channels > 5:
            score += 0.2
        elif user_channels > 2:
            score += 0.1

        # Signal 2 & 3: Link cross-channel and multi-user sharing
        if links:
            max_link_channels = 0
            max_link_users = 0
            for link in links:
                if link:
                    channels = await self.get_link_sharing_count(link)
                    users = await self.get_link_user_count(link)
                    max_link_channels = max(max_link_channels, channels)
                    max_link_users = max(max_link_users, users)

            # Same link in multiple channels is suspicious
            if max_link_channels > 5:
                score += 0.4
            elif max_link_channels > 2:
                score += 0.2

            # Same link shared by multiple users (coordinated)
            if max_link_users > 5:
                score += 0.3
            elif max_link_users > 2:
                score += 0.15

        return min(1.0, score)


graph_builder = GraphBuilder()
