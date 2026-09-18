"""
Простой синхронный слой работы с SQLite.
Для масштаба одного личного/командного бота этого достаточно —
никакого отдельного сервера БД поднимать не нужно.
"""

import sqlite3
import contextlib

from config import DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with contextlib.closing(get_conn()) as conn, conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                chat_id INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS places (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                google_place_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                address TEXT,
                maps_url TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id INTEGER NOT NULL,
                place_id INTEGER NOT NULL,
                notify INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (user_id, place_id),
                FOREIGN KEY (place_id) REFERENCES places (id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_reviews (
                place_id INTEGER NOT NULL,
                review_hash TEXT NOT NULL,
                PRIMARY KEY (place_id, review_hash),
                FOREIGN KEY (place_id) REFERENCES places (id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS review_texts (
                review_hash TEXT PRIMARY KEY,
                text TEXT NOT NULL
            )
            """
        )


# ---------- Пользователи ----------

def upsert_user(user_id: int, chat_id: int):
    with contextlib.closing(get_conn()) as conn, conn:
        conn.execute(
            "INSERT INTO users (user_id, chat_id) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET chat_id=excluded.chat_id",
            (user_id, chat_id),
        )


# ---------- Места ----------

def add_place(google_place_id: str, name: str, address: str, maps_url: str) -> int:
    """Возвращает internal id места (создаёт, если его ещё нет)."""
    with contextlib.closing(get_conn()) as conn, conn:
        conn.execute(
            "INSERT INTO places (google_place_id, name, address, maps_url) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(google_place_id) DO UPDATE SET name=excluded.name",
            (google_place_id, name, address, maps_url),
        )
        row = conn.execute(
            "SELECT id FROM places WHERE google_place_id = ?", (google_place_id,)
        ).fetchone()
        return row["id"]


def get_place(place_id: int):
    with contextlib.closing(get_conn()) as conn:
        return conn.execute("SELECT * FROM places WHERE id = ?", (place_id,)).fetchone()


def all_places_with_active_subscribers():
    """Места, у которых есть хотя бы один подписчик с включёнными уведомлениями."""
    with contextlib.closing(get_conn()) as conn:
        return conn.execute(
            """
            SELECT DISTINCT p.*
            FROM places p
            JOIN subscriptions s ON s.place_id = p.id
            WHERE s.notify = 1
            """
        ).fetchall()


def subscribers_for_place(place_id: int, notify_only: bool = True):
    query = (
        "SELECT u.chat_id, s.notify FROM subscriptions s "
        "JOIN users u ON u.user_id = s.user_id "
        "WHERE s.place_id = ?"
    )
    if notify_only:
        query += " AND s.notify = 1"
    with contextlib.closing(get_conn()) as conn:
        return [row["chat_id"] for row in conn.execute(query, (place_id,)).fetchall()]


# ---------- Подписки пользователя ----------

def subscribe(user_id: int, place_id: int):
    with contextlib.closing(get_conn()) as conn, conn:
        conn.execute(
            "INSERT INTO subscriptions (user_id, place_id, notify) VALUES (?, ?, 1) "
            "ON CONFLICT(user_id, place_id) DO UPDATE SET notify=1",
            (user_id, place_id),
        )


def unsubscribe(user_id: int, place_id: int):
    with contextlib.closing(get_conn()) as conn, conn:
        conn.execute(
            "DELETE FROM subscriptions WHERE user_id = ? AND place_id = ?",
            (user_id, place_id),
        )


def toggle_notify(user_id: int, place_id: int) -> bool:
    """Переключает уведомления, возвращает новое состояние (True/False)."""
    with contextlib.closing(get_conn()) as conn, conn:
        row = conn.execute(
            "SELECT notify FROM subscriptions WHERE user_id = ? AND place_id = ?",
            (user_id, place_id),
        ).fetchone()
        new_state = 0 if (row and row["notify"]) else 1
        conn.execute(
            "UPDATE subscriptions SET notify = ? WHERE user_id = ? AND place_id = ?",
            (new_state, user_id, place_id),
        )
        return bool(new_state)


def list_user_places(user_id: int):
    with contextlib.closing(get_conn()) as conn:
        return conn.execute(
            """
            SELECT p.id, p.name, p.address, p.maps_url, s.notify
            FROM subscriptions s
            JOIN places p ON p.id = s.place_id
            WHERE s.user_id = ?
            ORDER BY p.name
            """,
            (user_id,),
        ).fetchall()


def user_has_subscription(user_id: int, place_id: int) -> bool:
    with contextlib.closing(get_conn()) as conn:
        row = conn.execute(
            "SELECT 1 FROM subscriptions WHERE user_id = ? AND place_id = ?",
            (user_id, place_id),
        ).fetchone()
        return row is not None


# ---------- Отслеживание отзывов ----------

def is_review_seen(place_id: int, review_hash: str) -> bool:
    with contextlib.closing(get_conn()) as conn:
        row = conn.execute(
            "SELECT 1 FROM seen_reviews WHERE place_id = ? AND review_hash = ?",
            (place_id, review_hash),
        ).fetchone()
        return row is not None


def mark_review_seen(place_id: int, review_hash: str, text: str):
    with contextlib.closing(get_conn()) as conn, conn:
        conn.execute(
            "INSERT OR IGNORE INTO seen_reviews (place_id, review_hash) VALUES (?, ?)",
            (place_id, review_hash),
        )
        conn.execute(
            "INSERT OR REPLACE INTO review_texts (review_hash, text) VALUES (?, ?)",
            (review_hash, text),
        )


def get_review_text(review_hash: str):
    with contextlib.closing(get_conn()) as conn:
        row = conn.execute(
            "SELECT text FROM review_texts WHERE review_hash = ?", (review_hash,)
        ).fetchone()
        return row["text"] if row else None
