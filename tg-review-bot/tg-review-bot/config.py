import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "600"))
DB_PATH = os.getenv("DB_PATH", "reviewbot.db").strip()
API_LANGUAGE = os.getenv("API_LANGUAGE", "ru").strip()

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError(
        "Не задан TELEGRAM_BOT_TOKEN. Скопируйте .env.example в .env и заполните его."
    )
if not GOOGLE_API_KEY:
    raise RuntimeError(
        "Не задан GOOGLE_API_KEY. Скопируйте .env.example в .env и заполните его."
    )

# Языки, которые бот предложит при переводе отзыва
TRANSLATE_LANGUAGES = [
    ("🇷🇺 Русский", "ru"),
    ("🇬🇧 English", "en"),
    ("🇩🇪 Deutsch", "de"),
    ("🇫🇷 Français", "fr"),
    ("🇪🇸 Español", "es"),
    ("🇮🇹 Italiano", "it"),
    ("🇵🇱 Polski", "pl"),
    ("🇺🇦 Українська", "uk"),
    ("🇹🇷 Türkçe", "tr"),
    ("🇨🇳 中文", "zh-CN"),
]
