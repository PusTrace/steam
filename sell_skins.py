from dotenv import load_dotenv
import os
from datetime import datetime, timedelta, timezone

from bin.parsers import get_orders, get_history
from bin.steam import get_inventory, generate_steam_market_url, authorize_and_get_cookies, sell_skin
from bin.PostgreSQLDB import PostgreSQLDB
from bin.HistoryAnalyzer import preprocessing


def get_avg_price(avg_week_price, sell_orders):
    avg_sell_price = (sell_orders[0][0] + sell_orders[1][0] + sell_orders[2][0] + sell_orders[3][0] + sell_orders[4][0]) / 5 if sell_orders and len(sell_orders) >= 5 else 0
    avg_price = max(avg_week_price, avg_sell_price)
    print(f"Avg week price: {avg_week_price}, Avg sell price: {avg_sell_price}, Used avg price: {avg_price}")
    return avg_price*1.02

def update_data(skin, cursor, cookies):
    id, name, sell_orders_timestamp, analysis_timestamp, item_name_id = skin
    # Проверяем, нужно ли брать новые ордера
    if sell_orders_timestamp is None or sell_orders_timestamp < datetime.now(timezone.utc) - timedelta(days=1):
        print(f"Используем API для получения ордеров для {name} (ID: {id})")
        buy_orders, sell_orders = get_orders(item_name_id, sell_orders = True)
        db.insert_or_update_orders(skin[0], buy_orders, sell_orders)
        db.update_skin_orders_timestamp(skin[0], sell_orders=True)
        db.commit()
    else:
        print(f"Используем ордера базы данных для {name} (ID: {id})")
        cursor.execute("SELECT sell_orders FROM orders WHERE skin_id = %s", (id,))
        result = cursor.fetchone()
        if result:
            sell_orders = result[0]
        else:
            sell_orders = None

    # Проверяем, нужно ли брать новые цены
    if analysis_timestamp is None or analysis_timestamp < datetime.now(timezone.utc) - timedelta(days=7):
        print(f"Используем API для получения цен для {name} (ID: {id})")
        price_history = get_history(name, cookies)
        db.update_price_history(skin[0], price_history)
        db.update_skin_price_timestamp(skin[0])
        slope_six_m, slope_one_m, avg_month_price, avg_week_price, volume, high_approx, low_approx, moment_price = preprocessing(price_history)
        db.update_skins_analysis(skin[0], moment_price, volume, high_approx, low_approx, slope_six_m, slope_one_m, avg_month_price, avg_week_price)
        db.commit()
    else:
        cursor.execute("SELECT avg_week_price FROM skins WHERE id = %s", (id,))
        result = cursor.fetchone()
        if result:
            avg_week_price = result[0]
        else:
            avg_week_price = 0


    return avg_week_price, sell_orders

    

    

if __name__ == "__main__":
    cookies = authorize_and_get_cookies(only_cookies = True)

    # 2. connect to db
    load_dotenv()
    db = PostgreSQLDB(password=os.getenv("DEFAULT_PASSWORD"))

    # 3. get data from api
    inventory = get_inventory(cookies)
    db.log_completed_orders(inventory)
    db.commit()

    logs = db.get_completed_orders()
    skins = db.get_logged_skins()
    for log in logs:
        skin_name = log[9] # name
        print(f"Processing: '{skin_name}' .")
        asset_id = log[15] # asset_id
        my_price = log[2] # y
        skin_id = log[0] # id
        from_outside = log[19] # from_outside

        url = generate_steam_market_url(skin_name)

        skin_data = next(s for s in skins if s[1] == skin_name)

        avg_week_price, sell_orders = update_data(skin_data, db.cursor, cookies)
        
        avg_price = get_avg_price(avg_week_price, sell_orders)

        if from_outside:
            margin = None
            sell_price = avg_price
            print(f"margin: None. Selling for {sell_price:.2f}")
        else:
            margin = ((avg_price * 0.87) - my_price) * 100 / my_price

            if margin < 0:
                sell_price = my_price / 0.87
            else:
                sell_price = avg_price
            print(f"margin: {margin:.2f}%. Selling for {sell_price:.2f}")
            

        
        success = sell_skin(sell_price, asset_id, cookies)

        if success:
            db.log_placed_to_sell(asset_id, sell_price, margin)
            db.commit()
        else:
            print(f"Failed to sell {skin_name}.")

    db.close()

    