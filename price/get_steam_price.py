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
from utils.utils import save_data, generate_market_hash_name, signal_handler, run_router_script

# Константы для Steam API
STEAM_API_URL = "https://steamcommunity.com/market/priceoverview/"

MAX_RETRIES = 6  # Максимальное количество подряд идущих ошибок 429

def get_steam_price(market_hash_name):
    params = {
        "appid": "730",
        "currency": 37,
        "market_hash_name": market_hash_name
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
                "lowest_price": data.get("lowest_price"),
                "median_price": data.get("median_price"),
                "volume": data.get("volume"),
                "timestamp": datetime.now().isoformat()
            }
        else:
            print(f"Не удалось получить данные для {market_hash_name}")
            return None
            
    except requests.RequestException as e:
        print(f"Ошибка при запросе к Steam API для {market_hash_name}: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Ошибка при разборе JSON для {market_hash_name}: {e}")
        return None



if __name__ == "__main__":
    # Регистрируем обработчик сигнала
    signal.signal(signal.SIGINT, signal_handler)
    
    # Загружаем список скинов и существующую базу данных
    with open ("/home/pustrace/programming/trade/steam/database/skins.json", 'r', encoding='utf-8') as f:
        skins = json.load(f)
    with open ("/home/pustrace/programming/trade/steam/database/database.json", 'r', encoding='utf-8') as f:
        market_data = json.load(f)
    consecutive_429_errors = 0  # Счётчик ошибок 429 подряд
    today = date.today()  # Текущая дата

    for skin in skins:
        market_hash_names = generate_market_hash_name(skin)
        
        for market_hash_name in market_hash_names:
            if market_hash_name in market_data:
                print(f"'{market_hash_name}' уже существует")
                continue

            print(f"\nПолучение данных для {market_hash_name}...")
            item_data = get_steam_price(market_hash_name)
            
            if item_data:
                market_data[market_hash_name] = item_data
                save_data({market_hash_name: item_data}, "/home/pustrace/programming/trade/steam/database/database.json")
                consecutive_429_errors = 0
                time.sleep(3.5)
            else:
                consecutive_429_errors += 1
                if consecutive_429_errors >= MAX_RETRIES:
                    print("Достигнут лимит ошибок 429 подряд. Запускаем router.py.")
                    run_router_script()
                    consecutive_429_errors = 0
                time.sleep(40)

    print("Парсинг завершён.")
