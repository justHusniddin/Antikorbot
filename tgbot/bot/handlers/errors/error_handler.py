import logging
from aiogram import Router
from aiogram.types import ErrorEvent

router = Router()
logger = logging.getLogger(__name__)


@router.errors()
async def error_handler(event: ErrorEvent):
    """Global error handler"""

    logger.error(f"Update {event.update} caused error {event.exception}", exc_info=True)

    # You can add more sophisticated error handling here
    # For example, notify admins about critical errors

    return True
