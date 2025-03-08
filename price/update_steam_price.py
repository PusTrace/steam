import requests
import json
from datetime import datetime, date
import time
import signal
import sys
import os

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
from utils.utils import save_data, signal_handler
from price.get_steam_price import get_steam_price

# Константы для Steam API
STEAM_API_URL = "https://steamcommunity.com/market/priceoverview/"
MAX_RETRIES = 6  # Максимальное количество подряд идущих ошибок 


if __name__ == "__main__":
    # Регистрируем обработчик сигнала
    signal.signal(signal.SIGINT, signal_handler)
    
    # Загружаем список скинов и существующую базу данных
    with open("/home/pustrace/programming/trade/steam/database/perfect.json", 'r', encoding='utf-8') as f:
        skins = json.load(f)

    errors = 0  # Счётчик ошибок подряд
    today = date.today()  # Текущая дата

    for skin, data in skins.items():
        # Проверка, если у скина уже есть сегодняшний timestamp
        last_timestamp = data.get("timestamp")
        if last_timestamp:
            last_date = datetime.fromisoformat(last_timestamp).date()
            if last_date == today:
                print(f"Пропускаем {skin}, данные уже обновлены сегодня.")
                continue

        print(f"\nПолучение данных для {skin}...")
        item_data = get_steam_price(skin)
        
        if item_data:
            skins[skin] = item_data
            save_data(skins, "/home/pustrace/programming/trade/steam/database/perfect.json")
            errors = 0
            time.sleep(3.5)
        else:
            errors += 1
            if errors >= MAX_RETRIES:
                print("Достигнут лимит ошибок подряд. Запускаем router.py.")
                # run_router_script()
                time.sleep(6*60)
                errors = 0
            time.sleep(30)

    print("Парсинг завершён.")

