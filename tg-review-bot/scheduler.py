import asyncio
import logging

from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import database as db
import keyboards as kb
from google_places import get_place_details, GooglePlacesError
from utils import review_hash, format_review_message

logger = logging.getLogger(__name__)


async def poll_all_places(context: ContextTypes.DEFAULT_TYPE):
    places = db.all_places_with_active_subscribers()
    if not places:
        return
    logger.info("Опрашиваю %d мест на новые отзывы", len(places))
    for place in places:
        try:
            await _poll_one_place(context, place)
        except Exception:
            logger.exception("Ошибка при опросе места %s", place["name"])
        # небольшая пауза между запросами, чтобы не упереться в rate limit Google
        await asyncio.sleep(1)


async def _poll_one_place(context: ContextTypes.DEFAULT_TYPE, place):
    try:
        details = await asyncio.to_thread(get_place_details, place["google_place_id"])
    except GooglePlacesError as e:
        logger.warning("Google Places API ошибка для %s: %s", place["name"], e)
        return

    reviews = details.get("reviews", [])
    if not reviews:
        return

    subscribers = db.subscribers_for_place(place["id"], notify_only=True)
    if not subscribers:
        return

    # reviews_sort=newest -> идут от новых к старым, разворачиваем чтобы
    # рассылать в хронологическом порядке, если новых окажется несколько
    for review in reversed(reviews):
        r_hash = review_hash(place["google_place_id"], review)
        if db.is_review_seen(place["id"], r_hash):
            continue

        text = (review.get("text") or "").strip()
        db.mark_review_seen(place["id"], r_hash, text)

        message = format_review_message(details["name"] or place["name"], review)
        markup = kb.review_actions_keyboard(r_hash, details.get("maps_url") or place["maps_url"])
        photo_url = review.get("profile_photo_url")

        for chat_id in subscribers:
            try:
                if photo_url:
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=photo_url,
                        caption=message,
                        parse_mode=ParseMode.HTML,
                        reply_markup=markup,
                    )
                else:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode=ParseMode.HTML,
                        reply_markup=markup,
                    )
            except Exception:
                logger.exception("Не удалось отправить уведомление в чат %s", chat_id)
