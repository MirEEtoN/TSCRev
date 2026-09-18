"""
Тонкая обёртка над классическим (legacy) Google Places API.

Важные официальные ограничения Google, с которыми ничего не поделать:
  - Place Details отдаёт МАКСИМУМ 5 отзывов на место (обычно самых
    релевантных/новых), это ограничение самого API, не бота.
  - В объекте отзыва нет фотографий, приложенных к отзыву —
    только `profile_photo_url` (аватар автора). Отдельного эндпоинта
    "фото этого конкретного отзыва" у Google Places нет.

Если понадобится больше данных (например, фото отзывов), можно завести
отдельный модуль-адаптер (например, под SerpApi Google Maps Reviews) и
подключить его вместо/вместе с этим файлом — остальной код бота не
привязан к конкретному источнику данных, он ждёт от get_place_reviews()
и text_search() тот же формат словаря.
"""

import re
import urllib.parse
import requests

from config import GOOGLE_API_KEY, API_LANGUAGE

TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"


class GooglePlacesError(Exception):
    pass


def _check_status(data: dict):
    status = data.get("status")
    if status not in ("OK", "ZERO_RESULTS"):
        raise GooglePlacesError(
            f"Google Places API вернул статус {status}: {data.get('error_message', '')}"
        )


def text_search(query: str, max_results: int = 5) -> list[dict]:
    """Ищет места по текстовому запросу, возвращает список кандидатов."""
    params = {
        "query": query,
        "key": GOOGLE_API_KEY,
        "language": API_LANGUAGE,
    }
    resp = requests.get(TEXT_SEARCH_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    _check_status(data)
    results = data.get("results", [])[:max_results]
    return [
        {
            "place_id": r["place_id"],
            "name": r.get("name", "Без названия"),
            "address": r.get("formatted_address", ""),
        }
        for r in results
    ]


def get_place_details(place_id: str) -> dict:
    """Возвращает название, адрес, ссылку и отзывы (максимум 5, см. докстринг файла)."""
    params = {
        "place_id": place_id,
        "fields": "name,formatted_address,url,rating,user_ratings_total,reviews",
        "reviews_sort": "newest",
        "language": API_LANGUAGE,
        "key": GOOGLE_API_KEY,
    }
    resp = requests.get(PLACE_DETAILS_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    _check_status(data)
    result = data.get("result", {})
    return {
        "name": result.get("name", "Без названия"),
        "address": result.get("formatted_address", ""),
        "maps_url": result.get("url", ""),
        "rating": result.get("rating"),
        "user_ratings_total": result.get("user_ratings_total"),
        "reviews": result.get("reviews", []),
    }


_MAPS_PLACE_RE = re.compile(r"/maps/place/([^/]+)/")


def guess_query_from_maps_url(url: str) -> str | None:
    """
    Пытается вытащить человекочитаемое название места из ссылки Google Maps,
    например из https://www.google.com/maps/place/Some+Cafe/@... .
    Короткие ссылки (maps.app.goo.gl, goo.gl/maps) сначала разворачиваются
    обычным HTTP-редиректом.
    """
    try:
        if "maps.app.goo.gl" in url or "goo.gl/maps" in url:
            resp = requests.get(
                url,
                timeout=10,
                allow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            url = resp.url
        match = _MAPS_PLACE_RE.search(url)
        if not match:
            return None
        raw = match.group(1)
        decoded = urllib.parse.unquote(raw).replace("+", " ")
        return decoded
    except requests.RequestException:
        return None
