import requests
import json
from datetime import datetime
import time
import signal
import sys
import os

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
from utils.utils import save_data, signal_handler

# Константы для Steam API
STEAM_API_URL = "https://steamcommunity.com/market/itemordershistogram"

MAX_RETRIES = 6  # Максимальное количество подряд идущих ошибок 429


def get_steam_market_info(skin):
    params = {
        "country": "KZ",
        "language": "english",
        "currency": 37,
        "item_nameid": skin_id,
        "norender": 1
        
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(STEAM_API_URL, params=params, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("success"):
            return {
                "timestamp_orders": datetime.now().isoformat(),
                "buy_order_graph": data.get("buy_order_graph")     
            }
        else:
            print(f"Не удалось получить данные для {skin}")
            return None
            
    except requests.RequestException as e:
        print(f"Ошибка при запросе к Steam API для {skin}: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Ошибка при разборе JSON для {skin}: {e}")
        return None



if __name__ == "__main__":
    # Регистрируем обработчик сигнала
    signal.signal(signal.SIGINT, signal_handler)
    
    # Загружаем список скинов и существующую базу данных
    with open ("/home/pustrace/programming/trade/steam/database/perfect.json", "r", encoding="utf-8") as f:
        skins = json.load(f)
    with open ("/home/pustrace/programming/trade/steam/database/orders.json", "r", encoding="utf-8") as f:
        existing_data = json.load(f)
    with open ("/home/pustrace/programming/trade/steam/database/item_nameids.json", "r", encoding="utf-8") as f:
        item_nameids = json.load(f)
    consecutive_429_errors = 0  # Счётчик ошибок 429 подряд

    for skin, data in skins.items():
        if skin in existing_data:
            print(f"Данные для {skin} уже существуют.")
            continue
        # Извлекаем id для скина из второго JSON
        if skin in item_nameids:
            skin_id = item_nameids[skin]
        else:
            print(f"ID для {skin} не найден в item_nameids.json.")
            continue
        print(f"\nПолучение данных для {skin}...")
        item_data = get_steam_market_info(skin_id)
        
        if item_data:
            data[skin] = item_data
            save_data({skin: item_data}, "/home/pustrace/programming/trade/steam/database/orders.json")
            consecutive_429_errors = 0
            time.sleep(3.5)
        else:
            consecutive_429_errors += 1
            if consecutive_429_errors >= MAX_RETRIES:
                time.sleep(1*60*60)
                print("Превышено количество ошибок 429 подряд. Остановка на час.")
            time.sleep(40)

        print("Парсинг завершён.")
