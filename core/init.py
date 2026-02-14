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

def init_environment():
    """
    Инициализирует session, cookies, db
    Возвращает кортеж (session, cookies, db)
    """
    load_dotenv()
    
    # получаем cookies
    all_cookies = ensure_cookies()
    cookies = all_cookies.get("steamcommunity.com", {})
    
    # создаём session
    session = requests.Session()
    session.cookies.update(cookies)
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:146.0) Gecko/20100101 Firefox/146.0"
    })
    
    # подключаемся к БД
    db = PostgreSQLDB(host="192.168.88.50",password=os.getenv("DEFAULT_PASSWORD"))
    
    return session, cookies, db

