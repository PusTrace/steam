import requests
import json
import time
import os

def get_price_history(market_hash_name):
    base_url = "https://steamcommunity.com/market/pricehistory/"
    params = {
        "appid": 730,
        "market_hash_name": market_hash_name,
        "currency": 1
    }

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    cookies = {
        "steamLoginSecure": os.getenv("STEAM_LOGIN_SECURE")
    }

    response = requests.get(base_url, params=params, headers=headers, cookies=cookies)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Ошибка {response.status_code}: {response.reason} для {market_hash_name}")
        return None

def save_to_json(data, filename="main/database/price_history.json"):
    """Сохраняет данные в JSON, дописывая новые записи"""
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            try:
                existing_data = json.load(f)
            except json.JSONDecodeError:
                existing_data = {}
    else:
        existing_data = {}

    existing_data.update(data)  # Добавляем новые данные

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    
    with open("main/database/perfect.json", 'r', encoding='utf-8') as f:
        skins = json.load(f)
    
    price_data = {}
    
    for skin in skins:
        print(skin)
        data = get_price_history(skin)
        if data:
            price_data[skin] = data
            save_to_json({skin: data})
            time.sleep(2)
