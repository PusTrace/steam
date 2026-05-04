"""
Инициализация окружения для всех модулей
Вместо GlobalState - явная передача зависимостей
"""

import os
import logging
import requests
from dotenv import load_dotenv

from core.db import PostgreSQLDB
from core.steam.cookies import ensure_cookies

log = logging.getLogger("init")

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/118.0.5993.118 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}


def init_environment():
    """
    Инициализирует session, cookies, db
    Возвращает кортеж (session, cookies, db)
    """
    load_dotenv()

    # получаем cookies
    all_cookies = ensure_cookies()
    cookies = all_cookies.get("steamcommunity.com", {})

    log.debug(f"len(cookies): {len(cookies)}")
    # создаём session
    session = requests.Session()
    session.cookies.update(cookies)
    session.headers.update(BASE_HEADERS)
    log.debug("request session created")

    # подключаемся к БД
    db = PostgreSQLDB(host=os.getenv("DB_HOST"), password=os.getenv("DEFAULT_PASSWORD"))

    log.debug("db initialized")

    return session, cookies, db
