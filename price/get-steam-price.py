import requests
import json
from datetime import datetime
import time
import signal
import sys
import subprocess  # Для вызова программы router.py

# Константы для Steam API
STEAM_API_URL = "https://steamcommunity.com/market/priceoverview/"

MAX_RETRIES = 6  # Максимальное количество подряд идущих ошибок 429

def get_steam_market_info(market_hash_name):
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

def save_market_data(new_data, filename):
    """Сохраняет или обновляет данные в JSON файле"""
    try:
        # Пытаемся прочитать существующие данные
        with open(filename, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
        # Обновляем только новые данные
        existing_data.update(new_data)
        # Сохраняем обновленные данные
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=4)
        print(f"Данные успешно сохранены в {filename}")
    except Exception as e:
        print(f"Ошибка при сохранении данных: {e}")

def generate_market_hash_name(skin):
    """Генерирует полное название предмета для Steam Market"""
    wear_conditions = [
        "Factory New",
        "Minimal Wear",
        "Field-Tested",
        "Well-Worn",
        "Battle-Scarred"
    ]
    market_names = []
    market_names.extend(f"StatTrak™ {skin} ({wear})" for wear in wear_conditions)
    market_names.extend(f"{skin} ({wear})" for wear in wear_conditions)
    return market_names

def signal_handler(signum, frame):
    """Обработчик сигнала прерывания"""
    global market_data
    print("\nПолучен сигнал прерывания. Сохраняем данные перед выходом...")
    if 'market_data' in globals() and market_data:
        save_market_data(market_data, "/home/pustrace/programming/trade/steam/database/database.json")
    print("Данные сохранены. Завершение работы.")
    sys.exit(0)

def run_router_script():
    """Запускает router.py"""
    try:
        subprocess.run(["python", "/home/pustrace/programming/trade/steam/utils/router.py"], check=True)
        print("router.py успешно запущен.")
        print("Ожидаем 6.5 минут...")
        time.sleep(400)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при запуске router.py: {e}")

if __name__ == "__main__":
    # Регистрируем обработчик сигнала
    signal.signal(signal.SIGINT, signal_handler)
    
    # Загружаем список скинов и существующую базу данных
    with open ("/home/pustrace/programming/trade/steam/database/skins.json", 'r', encoding='utf-8') as f:
        skins = json.load(f)
    with open ("/home/pustrace/programming/trade/steam/database/database.json", 'r', encoding='utf-8') as f:
        market_data = json.load(f)
    consecutive_429_errors = 0  # Счётчик ошибок 429 подряд

    for skin in skins:
        market_hash_names = generate_market_hash_name(skin)
        
        for market_hash_name in market_hash_names:
            if market_hash_name in market_data:
                print(f"'{market_hash_name}' уже существует")
                continue

            print(f"\nПолучение данных для {market_hash_name}...")
            item_data = get_steam_market_info(market_hash_name)
            
            if item_data:
                market_data[market_hash_name] = item_data
                save_market_data({market_hash_name: item_data}, "/home/pustrace/programming/trade/steam/database/database.json")
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
