import asyncio
import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import database as db
import keyboards as kb
from google_places import text_search, get_place_details, guess_query_from_maps_url, GooglePlacesError
from translator import translate_text
from utils import format_review_message

logger = logging.getLogger(__name__)

HELP_TEXT = (
    "Я слежу за отзывами компаний в Google Maps и присылаю уведомления, когда "
    "появляется новый отзыв (оценка, текст, автор), с кнопками перевода и "
    "переходом к отзыву.\n\n"
    "<b>Команды:</b>\n"
    "/addplace — добавить новое место для отслеживания\n"
    "/myplaces — список моих мест: включить/выключить уведомления, удалить\n"
    "/cancel — отменить текущее добавление места\n"
    "/help — это сообщение\n\n"
    "⚠️ Ограничение самого Google Places API: доступно не более 5 последних "
    "отзывов на место, и фото прикреплённые к отзыву API не отдаёт (только "
    "аватар автора)."
)


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    db.upsert_user(user.id, chat.id)
    await update.message.reply_html(
        f"Привет, {user.first_name}! 👋\n\n{HELP_TEXT}"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(HELP_TEXT)


async def addplace_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting_place_query"] = True
    await update.message.reply_text(
        "Пришлите название компании (лучше вместе с городом), либо ссылку "
        "на Google Maps на это место.\n\nОтменить — /cancel"
    )


async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("awaiting_place_query", None)
    context.user_data.pop("search_results", None)
    await update.message.reply_text("Ок, отменено.")


async def myplaces_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send_myplaces(update.effective_user.id, update.message.reply_text)


async def _send_myplaces(user_id: int, send_func):
    places = db.list_user_places(user_id)
    if not places:
        await send_func("Вы пока не отслеживаете ни одного места. Используйте /addplace.")
        return
    markup = kb.myplaces_keyboard(places)
    await send_func("Ваши места:", reply_markup=markup)


async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_place_query"):
        return  # обычный текст без контекста — просто игнорируем

    query_raw = update.message.text.strip()
    context.user_data["awaiting_place_query"] = False

    query = query_raw
    if "google.com/maps" in query_raw or "goo.gl/maps" in query_raw or "maps.app.goo.gl" in query_raw:
        guessed = await asyncio.to_thread(guess_query_from_maps_url, query_raw)
        if guessed:
            query = guessed
        else:
            await update.message.reply_text(
                "Не удалось разобрать ссылку — пришлите, пожалуйста, название "
                "компании и город текстом."
            )
            return

    await update.message.reply_text(f"Ищу «{query}»…")

    try:
        results = await asyncio.to_thread(text_search, query)
    except GooglePlacesError as e:
        await update.message.reply_text(f"Ошибка Google Places API: {e}")
        return
    except Exception:
        logger.exception("text_search failed")
        await update.message.reply_text("Не получилось выполнить поиск, попробуйте позже.")
        return

    if not results:
        await update.message.reply_text(
            "Ничего не нашлось. Попробуйте уточнить запрос (добавьте город)."
        )
        return

    context.user_data["search_results"] = results
    lines = ["Нашёл несколько вариантов, выберите нужный:\n"]
    for i, r in enumerate(results, start=1):
        lines.append(f"{i}. <b>{r['name']}</b>\n{r['address']}")
    await update.message.reply_html(
        "\n\n".join(lines), reply_markup=kb.search_results_keyboard(len(results))
    )


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data.startswith("confirm_add:"):
        await _handle_confirm_add(update, context, int(data.split(":", 1)[1]))
    elif data == "cancel_add":
        context.user_data.pop("search_results", None)
        await query.edit_message_text("Отменено.")
    elif data.startswith("toggle:"):
        await _handle_toggle(update, context, int(data.split(":", 1)[1]))
    elif data.startswith("remove:"):
        await _handle_remove(update, context, int(data.split(":", 1)[1]))
    elif data.startswith("tr:"):
        review_hash = data.split(":", 1)[1]
        await query.edit_message_reply_markup(reply_markup=kb.language_keyboard(review_hash))
    elif data.startswith("trback:"):
        review_hash = data.split(":", 1)[1]
        text = db.get_review_text(review_hash)
        maps_url = None  # ссылка уже была в исходном сообщении, кнопку "назад" достаточно вернуть без неё
        await query.edit_message_reply_markup(
            reply_markup=kb.review_actions_keyboard(review_hash, maps_url)
        )
    elif data.startswith("trlang:"):
        _, review_hash, lang = data.split(":", 2)
        await _handle_translate(update, context, review_hash, lang)


async def _handle_confirm_add(update: Update, context: ContextTypes.DEFAULT_TYPE, index: int):
    query = update.callback_query
    results = context.user_data.get("search_results")
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    db.upsert_user(user_id, chat_id)

    if not results or index >= len(results):
        await query.edit_message_text("Список результатов устарел, начните заново: /addplace")
        return

    chosen = results[index]
    await query.edit_message_text(f"Добавляю «{chosen['name']}»…")

    try:
        details = await asyncio.to_thread(get_place_details, chosen["place_id"])
    except Exception:
        logger.exception("get_place_details failed")
        await query.edit_message_text("Не удалось получить данные о месте, попробуйте позже.")
        return

    place_db_id = db.add_place(
        google_place_id=chosen["place_id"],
        name=details["name"],
        address=details["address"],
        maps_url=details["maps_url"],
    )
    db.subscribe(user_id, place_db_id)
    context.user_data.pop("search_results", None)

    await query.edit_message_text(
        f"✅ «{details['name']}» добавлено в отслеживание.\n"
        f"Уведомления включены. Управлять — /myplaces"
    )


async def _handle_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE, place_id: int):
    query = update.callback_query
    user_id = update.effective_user.id
    db.toggle_notify(user_id, place_id)
    places = db.list_user_places(user_id)
    if places:
        await query.edit_message_reply_markup(reply_markup=kb.myplaces_keyboard(places))
    else:
        await query.edit_message_text("Список мест пуст.")


async def _handle_remove(update: Update, context: ContextTypes.DEFAULT_TYPE, place_id: int):
    query = update.callback_query
    user_id = update.effective_user.id
    db.unsubscribe(user_id, place_id)
    places = db.list_user_places(user_id)
    if places:
        await query.edit_message_reply_markup(reply_markup=kb.myplaces_keyboard(places))
    else:
        await query.edit_message_text("Список мест пуст. Добавить новое — /addplace")


async def _handle_translate(update: Update, context: ContextTypes.DEFAULT_TYPE, review_hash: str, lang: str):
    query = update.callback_query
    original = db.get_review_text(review_hash)
    if not original:
        await query.message.reply_text("Текст отзыва не найден (возможно, он был без текста).")
        return
    try:
        translated = await asyncio.to_thread(translate_text, original, lang)
    except Exception:
        logger.exception("translate_text failed")
        await query.message.reply_text("Не получилось перевести текст, попробуйте другой язык позже.")
        return
    await query.message.reply_text(f"🌐 Перевод:\n\n{translated}")
