from aiohttp import web
import logging
from redis import asyncio as aioredis
from config import settings
import time

logger = logging.getLogger(__name__)

async def check_redis():
    """Check Redis connection"""
    try:
        redis = aioredis.from_url(settings.REDIS_URL)
        await redis.ping()
        await redis.close()
        return True
    except Exception as e:
        logger.error("redis_health_check_failed", error=str(e))
        return False

async def check_telegram(bot):
    """Check Telegram connection"""
    try:
        await bot.get_me()
        return True
    except Exception as e:
        logger.error("telegram_health_check_failed", error=str(e))
        return False

async def health_check(request):
    """Health check endpoint for Railway"""
    start_time = time.time()
    
    # Get bot instance from app
    bot = request.app['bot']
    
    # Perform health checks
    redis_ok = await check_redis()
    telegram_ok = await check_telegram(bot)
    
    # Calculate response time
    response_time = time.time() - start_time
    
    # Prepare response
    status = 200 if redis_ok and telegram_ok else 500
    response = {
        'status': 'OK' if status == 200 else 'ERROR',
        'checks': {
            'redis': 'OK' if redis_ok else 'ERROR',
            'telegram': 'OK' if telegram_ok else 'ERROR'
        },
        'response_time': f"{response_time:.3f}s"
    }
    
    return web.json_response(response, status=status)

def setup_health_check(app, bot):
    """Setup health check routes"""
    app['bot'] = bot
    app.router.add_get('/health', health_check) 