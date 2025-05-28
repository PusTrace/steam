import requests
import os
import urllib3


# Отключаем предупреждения для небезопасных HTTPS-запросов
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_history(market_hash_name):
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