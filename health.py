from aiohttp import web
import logging
from redis import asyncio as aioredis
from config import settings
import time
import structlog
from typing import Tuple
import asyncio

logger = structlog.get_logger()

async def check_redis() -> Tuple[bool, str]:
    """Check Redis connection with retries"""
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            redis = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                retry_on_timeout=True,
                health_check_interval=30,
                socket_timeout=5.0,
                socket_connect_timeout=5.0,
                retry_on_error=[ConnectionError],
                encoding='utf-8'
            )
            await redis.ping()
            await redis.close()
            return True, "OK"
        except Exception as e:
            logger.error("redis_health_check_failed", 
                        error=str(e), 
                        attempt=attempt + 1, 
                        max_retries=max_retries)
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
            else:
                return False, str(e)

async def check_telegram(bot) -> Tuple[bool, str]:
    """Check Telegram connection with retries"""
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            await bot.get_me()
            return True, "OK"
        except Exception as e:
            logger.error("telegram_health_check_failed", 
                        error=str(e), 
                        attempt=attempt + 1, 
                        max_retries=max_retries)
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
            else:
                return False, str(e)

async def health_check(request):
    """Health check endpoint for Railway"""
    start_time = time.time()
    
    # Get bot instance from app
    bot = request.app['bot']
    
    # Perform health checks
    redis_ok, redis_msg = await check_redis()
    telegram_ok, telegram_msg = await check_telegram(bot)
    
    # Calculate response time
    response_time = time.time() - start_time
    
    # Prepare response
    status = 200 if redis_ok and telegram_ok else 503
    response = {
        'status': 'OK' if status == 200 else 'ERROR',
        'checks': {
            'redis': {
                'status': 'OK' if redis_ok else 'ERROR',
                'message': redis_msg
            },
            'telegram': {
                'status': 'OK' if telegram_ok else 'ERROR',
                'message': telegram_msg
            }
        },
        'response_time': f"{response_time:.3f}s"
    }
    
    return web.json_response(response, status=status)

def setup_health_check(app, bot):
    """Setup health check routes"""
    app['bot'] = bot
    app.router.add_get('/health', health_check) 