"""
Atlas AI Financial Assistant — Telegram entrypoint.
Run: python main.py
"""
import asyncio
import logging
import threading
import sys

# Fix for Windows + Python 3.10+
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from telegram.ext import Application, MessageHandler, filters
from config import settings
from db.session import init_db
from bot.handlers import start_or_message, handle_document, handle_photo, handle_voice
from oauth_server import run_oauth_server
from scheduler.jobs import start_scheduler

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("atlas")


async def post_init(app: Application):
    await init_db()
    start_scheduler(app.bot)
    logger.info("Database ready & scheduler started")


def main():
    # Ensure an event loop exists on the main thread
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # ... rest of the function stays the same
    
    # OAuth callback server in background thread
    if settings.GOOGLE_CLIENT_ID:
        t = threading.Thread(
            target=run_oauth_server,
            args=(settings.OAUTH_SERVER_PORT,),
            daemon=True,
        )
        t.start()
        logger.info("OAuth server listening on port %s", settings.OAUTH_SERVER_PORT)

    app = (
        Application.builder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Pure natural language — no CommandHandler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start_or_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))

    logger.info("Atlas is online — natural conversation mode")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
