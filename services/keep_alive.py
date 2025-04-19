import asyncio
import logging
from datetime import datetime
from aiogram import Bot
from config import settings

logger = logging.getLogger(__name__)

class KeepAliveService:
    def __init__(self, bot: Bot):
        self.bot = bot
        self._running = False
        self._task = None

    async def start(self):
        """Start the keep-alive service"""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._keep_alive_loop())
        logger.info("keep_alive_service_started")

    async def stop(self):
        """Stop the keep-alive service"""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("keep_alive_service_stopped")

    async def _keep_alive_loop(self):
        """Main keep-alive loop"""
        while self._running:
            try:
                # Проверяем соединение с Telegram
                await self.bot.get_me()
                
                # Логируем время последней активности
                logger.info("keep_alive_ping", timestamp=datetime.now().isoformat())
                
                # Ждем 5 минут перед следующей проверкой
                await asyncio.sleep(300)
            except Exception as e:
                logger.error("keep_alive_error", error=str(e))
                # При ошибке ждем меньше времени перед повторной попыткой
                await asyncio.sleep(60) 