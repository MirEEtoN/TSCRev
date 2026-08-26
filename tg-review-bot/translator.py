"""
Перевод текста отзывов через deep-translator (использует публичный
веб-интерфейс Google Translate, без API-ключа).

Это удобно для старта, но у такого способа нет гарантий SLA и он может
изредка отваливаться при изменениях на стороне Google. Если нужна
надёжность прод-уровня — замените реализацию translate_text() на вызов
официального Google Cloud Translation API (платный, но стабильный) —
остальной код бота трогать не придётся, он работает только с этой
функцией.
"""

from deep_translator import GoogleTranslator


def translate_text(text: str, target_lang: str) -> str:
    if not text:
        return ""
    translator = GoogleTranslator(source="auto", target=target_lang)
    return translator.translate(text)
