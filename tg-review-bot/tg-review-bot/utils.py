import hashlib


def review_hash(place_google_id: str, review: dict) -> str:
    """
    Стабильный короткий идентификатор отзыва — используется и чтобы
    не присылать один и тот же отзыв дважды, и как callback_data для
    кнопки перевода (поэтому он короткий, а не полный sha256).
    """
    raw = f"{place_google_id}:{review.get('author_name')}:{review.get('time')}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def stars_string(rating) -> str:
    if rating is None:
        return "нет оценки"
    filled = int(round(float(rating)))
    filled = max(0, min(5, filled))
    return "⭐" * filled + "☆" * (5 - filled)


def format_review_message(place_name: str, review: dict) -> str:
    author = review.get("author_name", "Аноним")
    rating = review.get("rating")
    text = (review.get("text") or "").strip()
    relative_time = review.get("relative_time_description", "")

    lines = [
        f"🏢 <b>{escape_html(place_name)}</b>",
        f"{stars_string(rating)}  ({rating}/5)" if rating is not None else "Без оценки",
        f"👤 {escape_html(author)}" + (f" · {escape_html(relative_time)}" if relative_time else ""),
    ]
    if text:
        lines.append("")
        lines.append(escape_html(text))
    else:
        lines.append("")
        lines.append("<i>(без текста, только оценка)</i>")
    return "\n".join(lines)


def escape_html(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
