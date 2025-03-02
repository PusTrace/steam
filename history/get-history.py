import requests
import json
import time
import os
import sys
from datetime import datetime, timedelta
import urllib3

# Получаем путь к родительской директории скрипта
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
from utils.utils import save_data

# Отключаем предупреждения для небезопасных HTTPS-запросов
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_price_history(market_hash_name):
    base_url = "https://steamcommunity.com/market/pricehistory/"
    params = {
        "appid": 730,
        "market_hash_name": market_hash_name,
        "currency": 1
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    cookies = {"steamLoginSecure": os.getenv("STEAM_LOGIN_SECURE")}
    
    try:
        # Временно отключаем проверку SSL (если требуется)
        response = requests.get(base_url, params=params, headers=headers, cookies=cookies, verify=False)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Ошибка {response.status_code}: {response.reason} для {market_hash_name}")
            return None
    except requests.exceptions.SSLError as e:
        print(f"SSL ошибка для {market_hash_name}: {e}")
        return None


def filter_price_history(price_data):
    if not price_data or "prices" not in price_data:
        return None

    prices = price_data["prices"]
    
    # Граница для последнего месяца
    last_month_date = datetime.now() - timedelta(days=30)
    
    filtered_prices = []
    first_entry_date = None
    
    for entry in prices:
        try:
            # Пример строки: "Sep 22 2021 01: +0"
            parts = entry[0].split()  # ["Sep", "22", "2021", "01:", "+0"]
            if len(parts) < 4:
                continue
            # Убираем двоеточие из часа
            hour = parts[3].replace(":", "")
            # Собираем строку: "Sep 22 2021 01"
            date_str = " ".join(parts[:3] + [hour])
            entry_date = datetime.strptime(date_str, "%b %d %Y %H")
            if first_entry_date is None:
                first_entry_date = entry_date.strftime("%Y-%m-%d")
            if entry_date >= last_month_date:
                filtered_prices.append(entry)
        except Exception as e:
            print(f"Ошибка при обработке даты {entry[0]}: {e}")
            continue
    
    return {
        "appearance_date": first_entry_date,
        "recent_prices": filtered_prices
    }


if __name__ == "__main__":
    with open("steam/database/filtred_price&volume.json", 'r', encoding='utf-8') as f:
        skins = json.load(f)
    
    with open("steam/database/price_history.json", 'r', encoding='utf-8') as f:
        price_data = json.load(f)
    
    for skin in skins:
        if skin in price_data:
            continue
        print(f"Обрабатывается: {skin}")
        raw_data = get_price_history(skin)
        if raw_data:
            filtered_data = filter_price_history(raw_data)
            if filtered_data:
                price_data[skin] = filtered_data
                save_data({skin: filtered_data}, "steam/database/price_history.json")
            time.sleep(2)