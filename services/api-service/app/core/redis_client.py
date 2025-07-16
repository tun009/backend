import json
import logging
from typing import Any, Optional, Union, Dict
import redis.asyncio as redis
from .config import settings

logger = logging.getLogger(__name__)

class RedisClient:
    """
    Redis client singleton for OBU Service.
    Handles connection pooling and basic cache operations.
    """
    _instance: Optional["RedisClient"] = None
    _client: Optional[redis.Redis] = None

    def __new__(cls) -> "RedisClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def initialize(cls) -> None:
        """Initialize Redis connection."""
        instance = cls()
        if instance._client is None:
            try:
                instance._client = redis.from_url(
                    settings.REDIS_URL,
                    max_connections=20,
                    decode_responses=True,
                    socket_timeout=5.0,
                    socket_connect_timeout=5.0,
                    health_check_interval=30
                )
                
                # Test connection
                await instance._client.ping()
                logger.info(f"✅ Redis connected successfully to {settings.REDIS_HOST}:{settings.REDIS_PORT}")
                
            except Exception as e:
                logger.error(f"❌ Failed to connect to Redis: {e}")
                raise

    @classmethod
    async def close(cls) -> None:
        """Close Redis connections."""
        instance = cls()
        if instance._client:
            await instance._client.aclose()
            instance._client = None
        logger.info("Redis connections closed")

    @classmethod
    def get_client(cls) -> redis.Redis:
        """Get Redis client instance."""
        instance = cls()
        if instance._client is None:
            raise RuntimeError("Redis client not initialized. Call initialize() first.")
        return instance._client

    @classmethod
    async def set(
        cls, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """Set a key-value pair in Redis with optional TTL."""
        try:
            client = cls.get_client()
            
            # Serialize value if it's not a string
            if not isinstance(value, str):
                value = json.dumps(value, default=str)
            
            if ttl:
                await client.setex(key, ttl, value)
            else:
                await client.set(key, value)
                
            logger.debug(f"Set cache key: {key} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"Redis SET failed for key {key}: {e}")
            return False

    @classmethod
    async def get(cls, key: str) -> Optional[Any]:
        """Get a value from Redis by key."""
        try:
            client = cls.get_client()
            value = await client.get(key)
            
            if value is None:
                return None
                
            # Try to deserialize JSON, fallback to string
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            logger.error(f"Redis GET failed for key {key}: {e}")
            return None

    @classmethod
    async def delete(cls, key: str) -> bool:
        """Delete a key from Redis."""
        try:
            client = cls.get_client()
            result = await client.delete(key)
            logger.debug(f"Deleted cache key: {key}")
            return result > 0
            
        except Exception as e:
            logger.error(f"Redis DELETE failed for key {key}: {e}")
            return False

    @classmethod
    async def exists(cls, key: str) -> bool:
        """Check if a key exists in Redis."""
        try:
            client = cls.get_client()
            result = await client.exists(key)
            return result > 0
            
        except Exception as e:
            logger.error(f"Redis EXISTS failed for key {key}: {e}")
            return False

    @classmethod
    async def delete_pattern(cls, pattern: str) -> int:
        """Delete all keys matching a pattern."""
        try:
            client = cls.get_client()
            keys = await client.keys(pattern)
            if keys:
                deleted = await client.delete(*keys)
                logger.debug(f"Deleted {deleted} keys matching pattern: {pattern}")
                return deleted
            return 0
            
        except Exception as e:
            logger.error(f"Redis DELETE_PATTERN failed for pattern {pattern}: {e}")
            return 0

    @classmethod
    async def set_hash(cls, name: str, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple fields in a Redis hash."""
        try:
            client = cls.get_client()
            
            # Serialize values that aren't strings
            serialized_mapping = {}
            for field, value in mapping.items():
                if not isinstance(value, str):
                    serialized_mapping[field] = json.dumps(value, default=str)
                else:
                    serialized_mapping[field] = value
            
            await client.hset(name, mapping=serialized_mapping) # type: ignore
            if ttl:
                await client.expire(name, ttl)
                
            logger.debug(f"Set hash: {name} with {len(mapping)} fields (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"Redis HSET failed for hash {name}: {e}")
            return False

    @classmethod
    async def get_hash(cls, name: str) -> Optional[Dict[str, Any]]:
        """Get all fields and values from a Redis hash."""
        try:
            client = cls.get_client()
            hash_data = await client.hgetall(name) # type: ignore
            
            if not hash_data:
                return None
                
            # Try to deserialize JSON values
            result = {}
            for field, value in hash_data.items():
                try:
                    result[field] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    result[field] = value
                    
            return result
            
        except Exception as e:
            logger.error(f"Redis HGETALL failed for hash {name}: {e}")
            return None

    @classmethod
    async def incr(cls, key: str, amount: int = 1, ttl: Optional[int] = None) -> Optional[int]:
        """Increment a counter in Redis."""
        try:
            client = cls.get_client()
            
            # Use pipeline for atomic operations
            async with client.pipeline() as pipe:
                result = await pipe.incrby(key, amount)
                if ttl:
                    await pipe.expire(key, ttl)
                results = await pipe.execute()
                
            return results[0] if results else None
            
        except Exception as e:
            logger.error(f"Redis INCR failed for key {key}: {e}")
            return None

# Create global instance
redis_client = RedisClient() 