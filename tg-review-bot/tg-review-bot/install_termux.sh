#!/data/data/com.termux/files/usr/bin/bash
set -e

echo "== Обновление пакетов Termux =="
pkg update -y && pkg upgrade -y

echo "== Установка системных зависимостей =="
# python — сам интерпретатор
# git — чтобы клонировать/обновлять репозиторий (по желанию)
# libjpeg-turbo, libxml2, libxslt — иногда нужны транзитивным зависимостям
#   requests/beautifulsoup, ставим сразу, чтобы не ловить ошибки сборки
pkg install -y python git libjpeg-turbo libxml2 libxslt

echo "== Обновление pip =="
pip install --upgrade pip

echo "== Установка Python-зависимостей проекта =="
pip install -r requirements.txt

echo "== Готово =="
echo "Дальше: cp .env.example .env && nano .env — впишите токен и API-ключ"
echo "Запуск: bash start.sh"
