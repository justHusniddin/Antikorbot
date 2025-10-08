# tgbot/bot/middlewares/throttling.py

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message
import time

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, time_limit: float = 0.5):
        self.time_limit = time_limit
        self.user_timestamps: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        current_time = time.time()
        last_time = self.user_timestamps.get(user_id)

        if last_time and (current_time - last_time) < self.time_limit:
            return
        self.user_timestamps[user_id] = current_time

        return await handler(event, data)
