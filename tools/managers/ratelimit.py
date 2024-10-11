import re
import inspect
import asyncio
import logging

from functools import wraps
from typing import Callable, Dict
from contextlib import suppress
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)
from cashews import cache

cache.setup("mem://")

def ratelimit(key: str, limit: int, duration: int = 60, retry: bool = True):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            arguments = inspect.signature(func).bind(*args, **kwargs)
            arguments.apply_defaults()

            formatted_key = key
            with suppress(Exception):
                formatted_key = key.format(**arguments.arguments)

            rl = await cache.get(formatted_key) or 0

            if rl < limit:
                await cache.set(formatted_key, rl + 1, expire=duration)
            elif rl >= limit and not retry:
                logger.info(f"{func.__name__} rate limited. Not retrying")
                return
            else:
                logger.info(
                    f"{func.__name__} rate limited. Trying again in {duration} seconds."
                )
                await asyncio.sleep(duration)

            return await func(*args, **kwargs)

        return wrapper

    return decorator