from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv

# database
from bin.PostgreSQLDB import PostgreSQLDB
# Models
from bin.pt_model import PTModel
# small scripts
from bin.parsers import get_orders, get_history
from bin.steam import authorize_and_get_cookies, buy_skin
from bin.utils import normalize_date
from bin.HistoryAnalyzer import preprocessing

def get_market_data(skin, cursor, cookies):
    id, name, orders_timestamp, price_timestamp, item_name_id = skin
    # Проверяем, нужно ли брать новые ордера
    if orders_timestamp is None or orders_timestamp < datetime.now(timezone.utc) - timedelta(days=2):
        print(f"Используем API для получения ордеров для {name} (ID: {id})")
        item_orders = get_orders(item_name_id)
    else:
        print(f"Используем ордера базы данных для {name} (ID: {id})")
        cursor.execute("SELECT data FROM orders WHERE skin_id = %s", (id,))
        result = cursor.fetchone()
        if result:
            item_orders = result[0]  # assuming data is in first column
        else:
            item_orders = None

    # Проверяем, нужно ли брать новые цены
    if price_timestamp is None or price_timestamp < datetime.now(timezone.utc) - timedelta(days=2):
        print(f"Используем API для получения цен для {name} (ID: {id})")
        item_price = get_history(name, cookies)
    else:
        print(f"Используем цены базы данных для {name} (ID: {id})")
        cursor.execute("SELECT date, price, volume FROM pricehistory WHERE skin_id = %s", (id,))
        item_price = cursor.fetchall()
        item_price = [[normalize_date(row[0]), row[1], row[2]] for row in item_price]

    return item_price, item_orders  # Успешно получили данные — возвращаем


def update_data(db: PostgreSQLDB, skin, cookies):
    price_history, skin_orders = get_market_data(skin, db.cursor, cookies)

    db.insert_or_update_orders(skin[0], skin_orders)
    db.update_skin_orders_timestamp(skin[0])
    db.commit()

    db.update_price_history(skin[0], price_history)
    db.update_skin_price_timestamp(skin[0])
    db.commit()
    return price_history, skin_orders


if __name__ == "__main__":
    model_type = "EVA"
    cookies, driver = authorize_and_get_cookies()
    load_dotenv()

    db = PostgreSQLDB("127.0.0.1", 5432, "steam", "postgres", os.getenv("DEFAULT_PASSWORD"))
    model = PTModel(model_type)

    skins = db.get_filtred_skins()

    for skin in skins:
        # get & update data in db
        history, skin_orders = update_data(db, skin, cookies)
        
        price, volume, approx_max, approx_min, linreg = preprocessing(history)
        db.update_skins_analysis(skin[0], price, volume, approx_max, approx_min, linreg)
        db.commit()

        if linreg is None or linreg < 0:
            print(f"Предсказание линейной регрессии для {skin[1]} (ID: {skin[0]}) не удалось или отрицательное.")
            continue
        # model prediction
        y, amount, profit, buy_volume = model.predict(
            price=price,
            volume=volume,
            skin_orders=skin_orders,
            linreg=linreg,
        )
        placed_snapshot = {
            "price": price,
            "sell_volume": volume,
            "buy_volume": buy_volume,
            "linreg": linreg,
            "skin_orders": skin_orders

        }
        # buy and log if y is not none
        if y is not None:
            buy_skin(driver, skin[1], y, amount)
            db.log_placement(skin[0], price, amount, profit, model_type, placed_snapshot)
            db.commit()

    driver.quit()
    db.close()