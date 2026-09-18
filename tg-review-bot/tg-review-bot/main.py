import logging

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

import database as db
from config import TELEGRAM_BOT_TOKEN, POLL_INTERVAL_SECONDS
from handlers import (
    start_cmd,
    help_cmd,
    addplace_cmd,
    cancel_cmd,
    myplaces_cmd,
    text_message_handler,
    callback_router,
)
from scheduler import poll_all_places

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)


def main():
    db.init_db()

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("addplace", addplace_cmd))
    application.add_handler(CommandHandler("cancel", cancel_cmd))
    application.add_handler(CommandHandler("myplaces", myplaces_cmd))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))
    application.add_handler(CallbackQueryHandler(callback_router))

    application.job_queue.run_repeating(
        poll_all_places, interval=POLL_INTERVAL_SECONDS, first=15
    )

    logging.info("Бот запущен, интервал опроса отзывов: %s сек.", POLL_INTERVAL_SECONDS)
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
