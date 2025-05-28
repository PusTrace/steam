from datetime import date, timedelta
import psycopg2
import os
from bin.get_order_info import get_orders
from bin.get_history import get_history

def get_market_data(skin, skin_id, timestamp_orders):
    proxies={"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"}
    today = date.today()  # Пример формата 'YYYY-MM-DD'
    yesterday = today - timedelta(days=1)

    
    errors = 0
    while errors < 6:
        # Если данные ордеров отсутствуют, запрашиваем их
        if not item_orders:
            item_orders = get_orders(skin_id, proxies)
            if item_orders:
                # Обновляем JSON-файл с ордерами
                save_data({skin: item_orders}, "/home/pustrace/programming/trade/steam/database/orders.json")
                errors = 0
                time.sleep(3.5)
            else:
                errors += 1
                if errors >= 2:
                    print("Превышено количество ошибок меняем айпи.")
                    change_ip()
                time.sleep(10)
        
        if item_price and item_orders:
            return item_price, item_orders
        
def main():
 conn = psycopg2.connect(
     dbname="steam",
     user="pustrace",
     password=os.getenv("DEFAULT_PASSWORD"),
     host="localhost",
     port="5432"
 )
    cursor = conn.cursor()
    cursor.execute("SELECT name, item_name_id, price FROM skins")

    item_price, item_orders = get_market_data(name, item_name_id, proxies)
    
    print(f"Item Price: {item_price}")
    print(f"Item Orders: {item_orders}")
        
if __name__ == "__main__":
    main()