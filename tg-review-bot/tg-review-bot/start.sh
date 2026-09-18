#!/data/data/com.termux/files/usr/bin/bash
# Держит телефон "разбуженным", чтобы Android не убивал процесс Termux в фоне.
# Требует установленный пакет termux-api (pkg install termux-api) и
# приложение Termux:API из того же источника, что и сам Termux (F-Droid).
if command -v termux-wake-lock >/dev/null 2>&1; then
    termux-wake-lock
fi

cd "$(dirname "$0")"
python3 main.py
