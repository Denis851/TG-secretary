from aiohttp import web
import logging
from redis import asyncio as aioredis
from config import settings
import time
import structlog
from typing import Tuple
import asyncio
import os
from aiogram import Bot

logger = structlog.get_logger()

# Application state keys
REDIS_CLIENT_KEY = web.AppKey('redis_client', aioredis.Redis)
BOT_KEY = web.AppKey('bot', Bot)
APP_STATE_KEY = web.AppKey('app_state', dict)

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

def setup_health_check(app: web.Application, bot: Bot) -> None:
    """Setup health check endpoint"""
    app_state = {
        'startup_time': time.time(),
        'last_check_time': time.time(),
        'status': 'READY',
        'bot_info': None,
        'redis_status': 'unknown'
    }
    
    async def health_check(request: web.Request) -> web.Response:
        try:
            # Update bot info
            if not app_state['bot_info']:
                try:
                    app_state['bot_info'] = await bot.get_me()
                except Exception as e:
                    logger.error("Failed to get bot info", error=str(e))
            
            # Check Redis connection
            redis_client = request.app.get(REDIS_CLIENT_KEY)
            if redis_client:
                try:
                    await redis_client.ping()
                    app_state['redis_status'] = 'connected'
                except Exception as e:
                    app_state['redis_status'] = 'error'
                    logger.error("Redis health check failed", error=str(e))
            
            # Update check time
            app_state['last_check_time'] = time.time()
            
            return web.json_response({
                'status': app_state['status'],
                'uptime': time.time() - app_state['startup_time'],
                'last_check': app_state['last_check_time'],
                'bot_info': str(app_state['bot_info']) if app_state['bot_info'] else None,
                'redis_status': app_state['redis_status']
            })
            
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return web.json_response({
                'status': 'ERROR',
                'error': str(e)
            }, status=500)
    
    # Store app state
    app[APP_STATE_KEY] = app_state
    
    # Register health check route using add_route
    app.router.add_route('GET', '/health', health_check)

    logger.info("Health check endpoint setup completed") 