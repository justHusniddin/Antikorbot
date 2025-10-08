import asyncio
import logging
from django.core.management.base import BaseCommand
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from tgbot.bot.loader import bot, dp
from tgbot.bot.handlers.users import start, complaint, admin as admin_handler
from tgbot.bot.handlers.errors import error_handler
from tgbot.bot.middlewares.throttling import ThrottlingMiddleware

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run Telegram Bot'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting bot...'))
        asyncio.run(main())


async def on_startup():
    logger.info("Bot is starting up...")
    await bot.delete_webhook(drop_pending_updates=True)
    dp.message.middleware(ThrottlingMiddleware(time_limit=0.5))
    dp.include_router(start.router)
    dp.include_router(complaint.router)
    dp.include_router(admin_handler.router)
    dp.include_router(error_handler.router)
    from aiogram.types import BotCommand, BotCommandScopeDefault

    commands = [
        BotCommand(command="start", description="Start bot / Botni ishga tushirish"),
        BotCommand(command="admin", description="Admin panel (admins only)"),
    ]

    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())

    logger.info("Bot started successfully!")


async def on_shutdown():
    logger.info("Bot is shutting down...")
    await bot.session.close()
    logger.info("Bot stopped!")


async def main():

    try:
        await on_startup()
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True
        )

    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await on_shutdown()
