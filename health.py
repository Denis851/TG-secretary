from aiohttp import web
import logging
from redis import asyncio as aioredis
from config import settings
import time
import structlog
from typing import Tuple
import asyncio
import os

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
    """Enhanced health check endpoint with detailed status information"""
    try:
        # Get application state
        app_state = request.app.get('app_state', {})
        initialization_stage = app_state.get('initialization_stage', 'unknown')
        startup_time = app_state.get('startup_time', time.time())
        uptime = time.time() - startup_time
        
        # Get Redis status
        redis_status = "unknown"
        if request.app.get('redis_client'):
            try:
                await request.app['redis_client'].ping()
                redis_status = "connected"
            except Exception as e:
                redis_status = f"error: {str(e)}"
        
        # Get bot status
        bot_status = "unknown"
        if request.app.get('bot'):
            try:
                bot_info = await request.app['bot'].get_me()
                bot_status = f"connected as @{bot_info.username}"
            except Exception as e:
                bot_status = f"error: {str(e)}"
        
        # Prepare response
        response = {
            'status': 'healthy' if initialization_stage == 'ready' else 'starting',
            'initialization_stage': initialization_stage,
            'uptime_seconds': round(uptime, 2),
            'startup_time': startup_time,
            'redis_status': redis_status,
            'bot_status': bot_status,
            'environment': os.getenv('RAILWAY_ENVIRONMENT', 'unknown'),
            'version': os.getenv('RAILWAY_GIT_COMMIT_SHA', 'unknown')
        }
        
        # Set appropriate status code
        status_code = 200 if initialization_stage == 'ready' else 503
        
        return web.json_response(response, status=status_code)
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return web.json_response({
            'status': 'error',
            'error': str(e)
        }, status=500)

def setup_health_check(app, bot):
    """Setup health check endpoint with application state tracking"""
    app['app_state'] = {
        'startup_time': time.time(),
        'initialization_stage': 'starting'
    }
    
    # Add health check endpoint
    app.router.add_get('/health', health_check)
    
    # Update state when application is ready
    app['app_state']['initialization_stage'] = 'ready'
    logger.info("Health check endpoint setup completed") 