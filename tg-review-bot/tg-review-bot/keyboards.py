from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import TRANSLATE_LANGUAGES


def search_results_keyboard(count: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(f"Вариант {i + 1}", callback_data=f"confirm_add:{i}")]
        for i in range(count)
    ]
    rows.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_add")])
    return InlineKeyboardMarkup(rows)


def myplaces_keyboard(places) -> InlineKeyboardMarkup:
    rows = []
    for p in places:
        bell = "🔔" if p["notify"] else "🔕"
        rows.append(
            [
                InlineKeyboardButton(
                    f"{bell} {p['name']}", callback_data=f"toggle:{p['id']}"
                ),
                InlineKeyboardButton("❌ Удалить", callback_data=f"remove:{p['id']}"),
            ]
        )
    return InlineKeyboardMarkup(rows) if rows else None


def review_actions_keyboard(review_hash: str, maps_url: str) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton("🌐 Перевести", callback_data=f"tr:{review_hash}")]]
    if maps_url:
        rows.append([InlineKeyboardButton("🔗 Открыть на картах", url=maps_url)])
    return InlineKeyboardMarkup(rows)


def language_keyboard(review_hash: str) -> InlineKeyboardMarkup:
    rows = []
    row = []
    for label, code in TRANSLATE_LANGUAGES:
        row.append(InlineKeyboardButton(label, callback_data=f"trlang:{review_hash}:{code}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("« Назад", callback_data=f"trback:{review_hash}")])
    return InlineKeyboardMarkup(rows)
