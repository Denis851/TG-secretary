from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from redis import asyncio as aioredis
import time
import logging
from config import settings

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, redis: aioredis.Redis, rate_limit: int = 20, period: int = 60):
        self.redis = redis
        self.rate_limit = rate_limit
        self.period = period

    async def __call__(self, handler, event, data):
        # Get user ID from different types of updates
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        else:
            return await handler(event, data)

        # Skip rate limiting for admin user
        if user_id == settings.USER_ID:
            return await handler(event, data)

        key = f"rate_limit:{user_id}"
        
        try:
            current = await self.redis.incr(key)
            if current == 1:
                await self.redis.expire(key, self.period)
                
            if current > self.rate_limit:
                logger.warning(f"Rate limit exceeded for user {user_id}")
                if isinstance(event, Message):
                    await event.answer("⚠️ Слишком много запросов. Пожалуйста, подождите.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("⚠️ Слишком много запросов", show_alert=True)
                return
                
            return await handler(event, data)
            
        except Exception as e:
            logger.error(f"Rate limit error: {e}")
            return await handler(event, data) 