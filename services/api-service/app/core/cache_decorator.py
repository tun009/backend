import functools
import logging
from typing import Any, Callable, Optional
from fastapi import Request
from .redis_client import redis_client
from .config import settings

logger = logging.getLogger(__name__)

def cache(
    key_prefix: str,
    ttl: Optional[int] = None,
    resource_id_param: str = "id"
) -> Callable:
    """
    Cache decorator for OBU Service endpoints.
    
    Args:
        key_prefix: Prefix for cache key (e.g., "vehicle", "alert", "location")
        ttl: Time to live in seconds (uses default from settings if None)
        resource_id_param: Name of the parameter to use as resource ID
    
    Usage:
        @cache(key_prefix="vehicle", ttl=300)
        async def get_vehicle(vehicle_id: UUID):
            # This will be cached as "vehicle:{vehicle_id}"
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Skip caching if disabled
            if not settings.CACHE_ENABLED:
                return await func(*args, **kwargs)
            
            # Extract resource ID from kwargs
            resource_id = kwargs.get(resource_id_param)
            if resource_id is None:
                logger.warning(f"Cache key parameter '{resource_id_param}' not found in {func.__name__}")
                return await func(*args, **kwargs)
            
            # Generate cache key
            cache_key = f"obu:{key_prefix}:{resource_id}"
            
            # Check if this is a GET request (cacheable)
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            is_get_request = request is None or request.method == "GET"
            
            if is_get_request:
                # Try to get from cache first
                try:
                    cached_result = await redis_client.get(cache_key)
                    if cached_result is not None:
                        logger.debug(f"Cache HIT for key: {cache_key}")
                        return cached_result
                except Exception as e:
                    logger.warning(f"Cache GET failed for {cache_key}: {e}")
            
            # Execute the function
            result = await func(*args, **kwargs)
            
            # Cache the result for GET requests
            if is_get_request and result is not None:
                try:
                    cache_ttl = ttl or settings.DEFAULT_CACHE_TTL
                    await redis_client.set(cache_key, result, cache_ttl)
                    logger.debug(f"Cache SET for key: {cache_key} (TTL: {cache_ttl}s)")
                except Exception as e:
                    logger.warning(f"Cache SET failed for {cache_key}: {e}")
            
            # Invalidate cache for non-GET requests (POST, PUT, DELETE)
            elif not is_get_request:
                try:
                    await redis_client.delete(cache_key)
                    logger.debug(f"Cache INVALIDATED for key: {cache_key}")
                except Exception as e:
                    logger.warning(f"Cache INVALIDATION failed for {cache_key}: {e}")
            
            return result
        
        return wrapper
    return decorator

def cache_vehicle_location(ttl: Optional[int] = None):
    """Specialized cache decorator for vehicle locations."""
    cache_ttl = ttl or settings.VEHICLE_LOCATION_TTL
    return cache("vehicle_location", cache_ttl, "vehicle_id")

def cache_dashboard_metrics(ttl: Optional[int] = None):
    """Specialized cache decorator for dashboard metrics."""
    cache_ttl = ttl or settings.DASHBOARD_METRICS_TTL
    return cache("dashboard_metrics", cache_ttl, "org_id")

def cache_active_alerts(ttl: Optional[int] = None):
    """Specialized cache decorator for active alerts."""
    cache_ttl = ttl or settings.ALERTS_TTL
    return cache("active_alerts", cache_ttl, "vehicle_id")

async def invalidate_vehicle_cache(vehicle_id: str) -> None:
    """
    Helper function to invalidate all cache related to a vehicle.
    Use this when vehicle data is updated.
    """
    try:
        patterns = [
            f"obu:vehicle:{vehicle_id}",
            f"obu:vehicle_location:{vehicle_id}",
            f"obu:active_alerts:{vehicle_id}"
        ]
        
        for pattern in patterns:
            await redis_client.delete(pattern)
            
        logger.info(f"Invalidated all cache for vehicle: {vehicle_id}")
    except Exception as e:
        logger.error(f"Cache invalidation failed for vehicle {vehicle_id}: {e}") 