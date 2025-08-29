import requests
import time
import requests
import time
from datetime import datetime, timezone
import random
import os
from dotenv import load_dotenv

from steam.bin.utils import normalize_date
from steam.bin.steam import authorize_and_get_cookies
from steam.bin.PostgreSQLDB import PostgreSQLDB

def get_orders(skin_id, sell_orders = False):
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
    while True:
        try:
            response = requests.get("https://steamcommunity.com/market/itemordershistogram", params=params, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("success"):
                print(f"Получены данные для {skin_id} (get_orders)")
                if sell_orders:
                    return data.get("buy_order_graph"), data.get("sell_order_graph")
                else:
                    return data.get("buy_order_graph")
            else:
                print(f"Не удалось получить данные для {skin_id}")
                return None
                
        except requests.RequestException as e:
            print(f"Ошибка при запросе к Steam API (get_orders) {e}")
            time.sleep(30)

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

            if not data.get("success") or not data.get("prices"):
                print(f"Нет данных по цене для {skin_name}")
                return None


            parsed_prices = []
            for entry in data.get("prices", []):
                raw_date = entry[0]  # "Sep 22 2021 01: +0"
                raw_price = entry[1]
                raw_volume = entry[2]
                try:
                    clean_date = raw_date.split(":")[0]
                    dt = datetime.strptime(clean_date, "%b %d %Y %H")
                    dt = dt.replace(tzinfo=timezone.utc)
                    dt = normalize_date(dt)

                    price = float(raw_price)
                    str_volume = str(raw_volume).replace(",", "").replace(" ", "")
                    volume = int(str_volume)
                    
                    parsed_prices.append([dt, price, volume])
                except Exception as e:
                    print(f"Ошибка парсинга строки: {entry} — {e}")
                    continue
            print(f"Получена история цен для {skin_name}")       
            return parsed_prices

        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе к Steam API: {e}")
            time.sleep(random.uniform(7.5, 12.0))
            errors += 1
        
def test_history():
    load_dotenv()
    skin_name = "StatTrak™ USP-S | Black Lotus (Battle-Scarred)"
    cookies, driver = authorize_and_get_cookies()
    history = get_history(skin_name, cookies)
    
    db = PostgreSQLDB(password=os.getenv("DEFAULT_PASSWORD"))
    db.update_price_history(245, history)
    db.commit()

    if history:
        print(f"Получена история цен для {skin_name}:")
        for entry in history:
            print(f"Дата: {entry[0]}, Цена: {entry[1]:.3f}, Объем: {entry[2]}")
        print(f"Всего записей: {len(history)}")
        print(f"Последняя запись: {history[-1]}")
    else:
        print(f"Не удалось получить историю цен для {skin_name}")
        
    driver.quit()
    db.close()
        
def test_orders():
    skin_id = 176262659  # Замените на реальный ID скина
    buy_order_graph, sell_order_graph = get_orders(skin_id, sell_orders=True)

    print(f"buy_order_graph для {skin_id}: {buy_order_graph}\n")
    
    print(f"sell_order_graph для {skin_id}: {sell_order_graph}")



if __name__ == "__main__":
    test_orders()