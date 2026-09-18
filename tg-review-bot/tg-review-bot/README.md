# Telegram-бот: уведомления о новых отзывах Google Maps

Бот отслеживает добавленные вами компании в Google Maps и присылает в
Telegram уведомление о каждом новом отзыве: оценка звёздами, автор,
текст, аватар автора, кнопка перевода текста и кнопка-ссылка на карточку
места в Google Maps.

Два варианта установки:
- **Ubuntu-сервер** (рекомендуется для круглосуточной работы) — см. ниже.
- **Termux на Android** — см. отдельный файл `TERMUX_SETUP.md`.

## ⚠️ Важно понимать заранее (ограничения Google, не бота)

- **Google Places API отдаёт не более 5 отзывов на место**.
- **Фотографий, прикреплённых к самому отзыву, Google Places API не
  отдаёт** — только аватар автора (`profile_photo_url`).
- У Google Places API есть квота и стоимость запросов — не ставьте
  `POLL_INTERVAL_SECONDS` слишком маленьким.

## 1. Подготовка на стороне Google

1. [Google Cloud Console](https://console.cloud.google.com/) → создайте
   проект.
2. Включите **Places API**.
3. Создайте API-ключ (APIs & Services → Credentials), ограничьте его по
   API и по возможности по IP.
4. Подключите биллинг.

## 2. Подготовка бота в Telegram

Напишите [@BotFather](https://t.me/BotFather) → `/newbot` → получите
токен.

## 3. Установка на Ubuntu

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip

cd ~/tg-review-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
nano .env   # впишите TELEGRAM_BOT_TOKEN и GOOGLE_API_KEY

python3 main.py   # проверка ручным запуском
```

### Автозапуск через systemd

```bash
sudo cp reviewbot.service /etc/systemd/system/reviewbot.service
sudo systemctl daemon-reload
sudo systemctl enable reviewbot
sudo systemctl start reviewbot
sudo journalctl -u reviewbot -f
```

## 4. Установка в Termux (Android)

Смотрите `TERMUX_SETUP.md` — там пошагово: установка пакетов, wake-lock
и автозапуск при перезагрузке телефона.

## 5. Команды бота

| Команда      | Что делает                                                          |
|--------------|----------------------------------------------------------------------|
| `/start`     | Регистрирует вас и показывает краткую справку                       |
| `/addplace`  | Добавить новое место (по названию+городу или по ссылке Google Maps) |
| `/myplaces`  | Список ваших мест: 🔔/🔕 (вкл/выкл уведомления) и ❌ (удалить)         |
| `/cancel`    | Отменить текущее добавление места                                   |
| `/help`      | Справка                                                              |

## 6. Как это работает внутри

- Раз в `POLL_INTERVAL_SECONDS` бот запрашивает у Google Places Details
  API до 5 последних отзывов по каждому месту, на которое хоть у кого-то
  включены уведомления.
- Каждый отзыв хешируется (место + автор + время) и сравнивается с уже
  отправленными (таблица `seen_reviews` в SQLite).
- Один отзыв рассылается всем подписчикам этого места с включёнными
  уведомлениями.

## 7. Структура проекта

```
tg-review-bot/
├── main.py              # точка входа
├── config.py             # чтение .env
├── database.py           # SQLite: пользователи, места, подписки, история
├── google_places.py      # обёртка над Google Places API
├── translator.py         # перевод текста отзывов
├── keyboards.py           # inline-клавиатуры
├── handlers.py            # команды и обработка кнопок
├── scheduler.py           # периодический опрос и рассылка
├── utils.py                # форматирование сообщений, хеш отзыва
├── requirements.txt
├── .env.example
├── reviewbot.service      # systemd unit (Ubuntu)
├── install_termux.sh      # установка зависимостей (Termux)
├── start.sh                # запуск с wake-lock (Termux)
└── TERMUX_SETUP.md         # подробная инструкция для Android
```
