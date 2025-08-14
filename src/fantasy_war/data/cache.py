"""Caching system for NFL data to improve performance."""

import hashlib
import pickle
from pathlib import Path
from typing import Any, Optional, Callable, Union
from datetime import datetime, timedelta

import diskcache as dc
from loguru import logger

from fantasy_war.config.settings import settings


class CacheManager:
    """Manages caching of NFL data and computed results."""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize cache manager.
        
        Args:
            cache_dir: Directory for cache storage. Uses settings default if None.
        """
        self.cache_dir = cache_dir or settings.cache.directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure cache with size limit
        max_size_bytes = int(settings.cache.max_size_gb * 1024**3)  # Convert GB to bytes
        
        self.cache = dc.Cache(
            str(self.cache_dir),
            size_limit=max_size_bytes,
            eviction_policy='least-recently-used'
        )
        
        self.default_ttl = timedelta(days=settings.cache.ttl_days)
        logger.info(f"Cache initialized at {self.cache_dir} with {settings.cache.max_size_gb}GB limit")
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        # Create a string representation of all arguments
        key_data = str(args) + str(sorted(kwargs.items()))
        
        # Hash to create consistent key
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if not settings.cache.enabled:
            return None
            
        try:
            return self.cache.get(key)
        except Exception as e:
            logger.warning(f"Cache get failed for key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> bool:
        """Set item in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live, uses default if None
            
        Returns:
            True if successfully cached
        """
        if not settings.cache.enabled:
            return False
            
        ttl_seconds = int((ttl or self.default_ttl).total_seconds())
        
        try:
            return self.cache.set(key, value, expire=ttl_seconds)
        except Exception as e:
            logger.warning(f"Cache set failed for key {key}: {e}")
            return False
    
    def cached_call(self, func: Callable, *args, ttl: Optional[timedelta] = None, **kwargs) -> Any:
        """Execute function with caching.
        
        Args:
            func: Function to execute
            *args: Function arguments
            ttl: Cache time to live
            **kwargs: Function keyword arguments
            
        Returns:
            Function result (cached or fresh)
        """
        # Generate cache key from function name and arguments
        func_name = f"{func.__module__}.{func.__name__}"
        cache_key = self._generate_key(func_name, *args, **kwargs)
        
        # Try to get from cache first
        cached_result = self.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for {func_name}")
            return cached_result
        
        # Execute function and cache result
        logger.debug(f"Cache miss for {func_name}, executing function")
        result = func(*args, **kwargs)
        
        if result is not None:
            self.set(cache_key, result, ttl)
            
        return result
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache keys matching pattern.
        
        Args:
            pattern: Pattern to match (contains matching)
            
        Returns:
            Number of keys invalidated
        """
        count = 0
        
        try:
            for key in list(self.cache):
                if pattern in str(key):
                    del self.cache[key]
                    count += 1
                    
            logger.info(f"Invalidated {count} cache entries matching '{pattern}'")
        except Exception as e:
            logger.warning(f"Cache invalidation failed: {e}")
            
        return count
    
    def clear_expired(self) -> int:
        """Clear expired cache entries.
        
        Returns:
            Number of entries cleared
        """
        try:
            cleared = self.cache.cull()
            logger.info(f"Cleared {cleared} expired cache entries")
            return cleared
        except Exception as e:
            logger.warning(f"Cache cleanup failed: {e}")
            return 0
    
    def clear_all(self) -> bool:
        """Clear all cache entries.
        
        Returns:
            True if successful
        """
        try:
            self.cache.clear()
            logger.info("Cleared all cache entries")
            return True
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False
    
    def get_stats(self) -> dict:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        try:
            stats = {
                'size_bytes': self.cache.volume(),
                'size_mb': round(self.cache.volume() / 1024**2, 2),
                'count': len(self.cache),
                'directory': str(self.cache_dir),
                'max_size_gb': settings.cache.max_size_gb,
                'ttl_days': settings.cache.ttl_days,
                'enabled': settings.cache.enabled,
            }
            return stats
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {}
    
    def close(self):
        """Close cache connection."""
        try:
            self.cache.close()
            logger.debug("Cache connection closed")
        except Exception as e:
            logger.warning(f"Error closing cache: {e}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Global cache manager instance  
cache_manager = CacheManager()