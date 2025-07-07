import requests
import time


def get_orders(skin_id):
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
                return data.get("buy_order_graph")
            else:
                print(f"Не удалось получить данные для {skin_id}")
                return None
                
        except requests.RequestException as e:
            print(f"Ошибка при запросе к Steam API (get_orders) {e}")
            time.sleep(30)

        
def test():
    skin_id = 176262659  # Замените на реальный ID скина
    orders = get_orders(skin_id)
    
    if orders:
        print(f"Получены ордера для скина {skin_id}: {orders}")
    else:
        print(f"Не удалось получить ордера для скина {skin_id}")
if __name__ == "__main__":
    test()