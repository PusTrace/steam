from dotenv import load_dotenv
import os
from datetime import datetime, timedelta, timezone

from bin.parsers import get_orders, get_history
from bin.steam import get_inventory, sell_skin, generate_steam_market_url, authorize_and_get_cookies
from bin.PostgreSQLDB import PostgreSQLDB


def get_avg_price(skin, cursor, cookies):
    id, name, orders_timestamp, price_timestamp, item_name_id = skin
    # Проверяем, нужно ли брать новые ордера
    if orders_timestamp is None or orders_timestamp < datetime.now(timezone.utc) - timedelta(days=1):
        print(f"Используем API для получения ордеров для {name} (ID: {id})")
        item_orders = get_orders(item_name_id, sell_order_graph = True)
    else:
        print(f"Используем ордера базы данных для {name} (ID: {id})")
        cursor.execute("SELECT data FROM orders WHERE skin_id = %s", (id,))
        result = cursor.fetchone()
        if result:
            item_orders = result[0]  # assuming data is in first column
        else:
            item_orders = None

    # Проверяем, нужно ли брать новые цены
    if price_timestamp is None or price_timestamp < datetime.now(timezone.utc) - timedelta(days=7):
        print(f"Используем API для получения цен для {name} (ID: {id})")
        price_history = get_history(name, cookies)
        db.update_price_history(skin[0], price_history)
        db.update_skin_price_timestamp(skin[0])
        db.commit()
    else:
        cursor.execute("select volume, avg_week_price from skins WHERE id = %s", (id,))


    return price_history, item_orders

    

if __name__ == "__main__":
    cookies = authorize_and_get_cookies(only_cookies = True)

    # 2. connect to db
    load_dotenv()
    db = PostgreSQLDB(password=os.getenv("DEFAULT_PASSWORD"))

    # 3. get data from api
    inventory = get_inventory(cookies)
    db.log_completed_orders(inventory)

    logs = db.get_completed_orders()
    skins = db.get_logged_skins()

    for log in logs:
        skin_name = log[14] # name
        print(f"Processing: '{skin_name}' .")
        list_of_assets = inventory[skin_name].get("asset_ids")
        my_price = log[2] # y
        skin_id = log[0] # id

        url = generate_steam_market_url(skin_name)

        skin_data = next(s for s in skins if s[1] == skin_name)

        avg_price = get_avg_price(skin_data, db.cursor, cookies)
        
        margin = ((avg_price * 0.87) - my_price) * 100 / my_price
        
        if margin < 0:
            sell_price = my_price / 0.87
        else:
            sell_price = avg_price
            

        print(f"margin: {margin:.2f}%. Selling for {sell_price:.2f}")

        sell_skin(sell_price, list_of_assets, cookies)
        db.log_placed_to_sell(skin_id, sell_price, margin)

    