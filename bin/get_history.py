import requests
import urllib3
import time
from datetime import datetime, timezone

# Отключаем предупреждения для небезопасных HTTPS-запросов
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_history(skin_name, raw_cookies):
    base_url = "https://steamcommunity.com/market/pricehistory/"
    params = {
        "appid": 730,
        "market_hash_name": skin_name,
        "currency": 1
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    errors = 0
    cookies = {cookie["name"]: cookie["value"] for cookie in raw_cookies}
    while errors < 5:
        try:
            response = requests.get(base_url, params=params, headers=headers, cookies=cookies, verify=False)
            response.raise_for_status()
            data = response.json()

            if not data.get("success"):
                print(f"Ответ от сервера без success=True для {skin_name}")
                return None

            parsed_prices = []
            for entry in data.get("prices", []):
                raw_date = entry[0]  # "Sep 22 2021 01: +0"
                raw_price = entry[1]
                raw_volume = entry[2]
                try:
                    clean_date = raw_date.split(" +")[0].strip(":")
                    dt = datetime.strptime(clean_date, "%b %d %Y %H").replace(tzinfo=timezone.utc)
                    iso_date = dt.isoformat()
                    price = float(raw_price)
                    str_volume = str(raw_volume).replace(",", "").replace(" ", "")
                    volume = int(str_volume)
                    parsed_prices.append([iso_date, price, volume])
                except Exception as e:
                    print(f"Ошибка парсинга строки: {entry} — {e}")
                    continue
            print(f"Получена история цен для {skin_name}")       
            return parsed_prices

        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе к Steam API: {e}")
            time.sleep(10)
            errors += 1
        
def test():
    skin_name = "USP-S | Black Lotus (Battle-Scarred)"
    raw_cookies = 0
    history = get_history(skin_name, raw_cookies)
    
    if history:
        print(f"Получена история цен для {skin_name}:")
        for entry in history:
            print(f"Дата: {entry[0]}, Цена: {entry[1]:.3f}, Объем: {entry[2]}")
        print(f"Всего записей: {len(history)}")
        print(f"Последняя запись: {history[-1]}")
    else:
        print(f"Не удалось получить историю цен для {skin_name}")

if __name__ == "__main__":
    test()
