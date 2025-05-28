import requests
import json
from datetime import datetime

def get_orders(skin_id, proxies):
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
        response = requests.get("https://steamcommunity.com/market/itemordershistogram", params=params, headers=headers, proxies=proxies)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("success"):
            return {
                "timestamp_orders": datetime.now().isoformat(),
                "buy_order_graph": data.get("buy_order_graph")     
            }
        else:
            print(f"Не удалось получить данные для {skin_id}")
            return None
            
    except requests.RequestException as e:
        print(f"Ошибка при запросе к Steam API {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Ошибка при разборе JSON {e}")
        return None