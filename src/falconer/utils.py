"""Utility functions for Falconer."""

import asyncio
import time
from functools import wraps
from typing import Any, Callable, Optional, Tuple, Type

import httpx

from .logging import get_logger

logger = get_logger(__name__)


def retry_on_network_error(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (httpx.HTTPError, ConnectionError, TimeoutError)
):
    """
    Decorator to retry a function on network errors with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 30.0)
        exponential_base: Base for exponential backoff (default: 2.0)
        exceptions: Tuple of exception types to catch and retry (default: httpx.HTTPError, ConnectionError, TimeoutError)

    Returns:
        Decorated function that retries on specified exceptions
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        delay = min(base_delay * (exponential_base ** attempt), max_delay)
                        logger.warning(
                            f"Network error in {func.__name__}, retrying in {delay:.2f}s",
                            attempt=attempt + 1,
                            max_attempts=max_attempts,
                            error=str(e)
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"Network error in {func.__name__}, max retries exceeded",
                            attempts=max_attempts,
                            error=str(e)
                        )

            # If we get here, all retries failed
            raise last_exception

        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        delay = min(base_delay * (exponential_base ** attempt), max_delay)
                        logger.warning(
                            f"Network error in {func.__name__}, retrying in {delay:.2f}s",
                            attempt=attempt + 1,
                            max_attempts=max_attempts,
                            error=str(e)
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"Network error in {func.__name__}, max retries exceeded",
                            attempts=max_attempts,
                            error=str(e)
                        )

            # If we get here, all retries failed
            raise last_exception

        # Return the appropriate wrapper based on whether the function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
