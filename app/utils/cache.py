"""
Redis caching utilities for GMet Weather API.

This module provides caching functionality using Redis to improve API performance
for frequently accessed data like current weather and station information.
"""

import json
import logging
from typing import Optional, Any
from functools import wraps

import redis
from redis.exceptions import RedisError

from app.config import settings
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class RedisCache:
    """
    Redis cache manager for weather data.

    Provides methods for caching and retrieving weather data with configurable TTL.
    """

    def __init__(self):
        """Initialize Redis connection."""
        self.client: Optional[redis.Redis] = None
        self.enabled = False
        self._connect()

    def _connect(self):
        """Establish connection to Redis."""
        try:
            self.client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.client.ping()
            self.enabled = True
            logger.info(f"✓ Redis cache connected: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        except (RedisError, ConnectionError) as e:
            logger.warning(f"⚠️  Redis cache unavailable: {e}. Caching disabled.")
            self.enabled = False
            self.client = None

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or cache disabled
        """
        if not self.enabled or not self.client:
            return None

        try:
            value = self.client.get(key)
            if value:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(value)
            logger.debug(f"Cache MISS: {key}")
            return None
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Cache GET error for key '{key}': {e}")
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: int = 300
    ) -> bool:
        """
        Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds (default: 5 minutes)

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.client:
            return False

        try:
            serialized = json.dumps(value, default=str)
            self.client.setex(key, ttl, serialized)
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return True
        except (RedisError, TypeError, ValueError) as e:
            logger.error(f"Cache SET error for key '{key}': {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key to delete

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.client:
            return False

        try:
            self.client.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return True
        except RedisError as e:
            logger.error(f"Cache DELETE error for key '{key}': {e}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching a pattern.

        Args:
            pattern: Redis key pattern (e.g., "weather:*")

        Returns:
            Number of keys deleted
        """
        if not self.enabled or not self.client:
            return 0

        try:
            keys = self.client.keys(pattern)
            if keys:
                deleted = self.client.delete(*keys)
                logger.info(f"Cache CLEAR: {deleted} keys matching '{pattern}'")
                return deleted
            return 0
        except RedisError as e:
            logger.error(f"Cache CLEAR error for pattern '{pattern}': {e}")
            return 0

    def health_check(self) -> dict:
        """
        Check Redis health status.

        Returns:
            Dict with health status information
        """
        if not self.enabled or not self.client:
            return {
                "status": "disabled",
                "message": "Redis caching is not enabled"
            }

        try:
            self.client.ping()
            info = self.client.info()
            return {
                "status": "healthy",
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "uptime_in_seconds": info.get("uptime_in_seconds", 0)
            }
        except RedisError as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Global cache instance
cache = RedisCache()


def cached(ttl: int = 300, key_prefix: str = "gmet"):
    """
    Decorator for caching function results.

    Usage:
        @cached(ttl=600, key_prefix="weather")
        async def get_current_weather(location: str):
            ...

    Args:
        ttl: Cache time-to-live in seconds
        key_prefix: Prefix for cache keys

    Returns:
        Decorated function with caching
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"

            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Call function and cache result
            result = await func(*args, **kwargs)

            # Cache the result
            cache.set(cache_key, result, ttl=ttl)

            return result

        return wrapper
    return decorator


# Cache key helpers
def make_cache_key(*parts: str) -> str:
    """
    Create a cache key from parts.

    Args:
        *parts: Parts to join into a cache key

    Returns:
        Cache key string

    Example:
        >>> make_cache_key("weather", "current", "DGAA")
        "weather:current:DGAA"
    """
    return ":".join(str(part) for part in parts)


# Pre-defined cache keys for common operations
CACHE_KEYS = {
    "current_weather": lambda station_code: make_cache_key("weather", "current", station_code),
    "station_list": lambda region=None: make_cache_key("stations", region or "all"),
    "station_detail": lambda code: make_cache_key("station", code),
    "latest_observation": lambda station_id: make_cache_key("observation", "latest", station_id),
}


# Cache TTL presets (in seconds)
CACHE_TTL = {
    "current_weather": 300,      # 5 minutes - weather changes relatively quickly
    "station_list": 3600,         # 1 hour - stations change rarely
    "station_detail": 3600,       # 1 hour
    "historical": 86400,          # 24 hours - historical data doesn't change
    "forecast": 1800,             # 30 minutes - forecasts update regularly
}
