"""
Redis client management
"""
from typing import Optional
import redis.asyncio as redis
from app.core.config import settings


class RedisClient:
    """Redis client manager"""

    def __init__(self):
        self.default_client: Optional[redis.Redis] = None
        self.session_client: Optional[redis.Redis] = None
        self.cache_client: Optional[redis.Redis] = None
        self.rate_limit_client: Optional[redis.Redis] = None

    async def connect(self):
        """Initialize Redis connections"""
        # Extract base URL properly - handle URLs with or without trailing /db
        redis_url = settings.REDIS_URL
        if redis_url.count('/') >= 3:
            # URL has a database number (e.g., redis://host:port/0)
            base_url = redis_url.rsplit("/", 1)[0]
        else:
            # URL doesn't have a database number (e.g., redis://host:port)
            base_url = redis_url

        self.default_client = await redis.from_url(
            f"{base_url}/0",  # Use explicit DB 0 for default
            encoding="utf-8",
            decode_responses=True,
        )

        self.session_client = await redis.from_url(
            f"{base_url}/{settings.REDIS_SESSION_DB}",
            encoding="utf-8",
            decode_responses=True,
        )

        self.cache_client = await redis.from_url(
            f"{base_url}/{settings.REDIS_CACHE_DB}",
            encoding="utf-8",
            decode_responses=True,
        )

        self.rate_limit_client = await redis.from_url(
            f"{base_url}/{settings.REDIS_RATE_LIMIT_DB}",
            encoding="utf-8",
            decode_responses=True,
        )

    async def close(self):
        """Close Redis connections"""
        if self.default_client:
            await self.default_client.close()
        if self.session_client:
            await self.session_client.close()
        if self.cache_client:
            await self.cache_client.close()
        if self.rate_limit_client:
            await self.rate_limit_client.close()

    async def get(self, key: str, db: str = "default") -> Optional[str]:
        """Get value from Redis"""
        client = self._get_client(db)
        return await client.get(key)

    async def set(
        self,
        key: str,
        value: str,
        expire: Optional[int] = None,
        db: str = "default",
    ) -> bool:
        """Set value in Redis"""
        client = self._get_client(db)
        return await client.set(key, value, ex=expire)

    async def delete(self, key: str, db: str = "default") -> int:
        """Delete key from Redis"""
        client = self._get_client(db)
        return await client.delete(key)

    async def exists(self, key: str, db: str = "default") -> bool:
        """Check if key exists in Redis"""
        client = self._get_client(db)
        return await client.exists(key) > 0

    async def increment(self, key: str, db: str = "default") -> int:
        """Increment value in Redis"""
        client = self._get_client(db)
        return await client.incr(key)

    async def expire(self, key: str, seconds: int, db: str = "default") -> bool:
        """Set expiry on key"""
        client = self._get_client(db)
        return await client.expire(key, seconds)

    def _get_client(self, db: str) -> redis.Redis:
        """Get Redis client by database name"""
        clients = {
            "default": self.default_client,
            "session": self.session_client,
            "cache": self.cache_client,
            "rate_limit": self.rate_limit_client,
        }
        return clients.get(db, self.default_client)


# Global Redis client instance
redis_client = RedisClient()


async def get_redis() -> RedisClient:
    """Dependency for getting Redis client"""
    return redis_client
