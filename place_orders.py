from datetime import datetime, timedelta, timezone
import os
import numpy as np
from dotenv import load_dotenv

# database
from bin.PostgreSQLDB import PostgreSQLDB
# Models
from bin.pt_model import PTModel
# small scripts
from bin.get_order_info import get_orders
from bin.get_history import get_history
from bin.steam import authorize_and_get_cookies, buy_skin
from bin.utils import normalize_date

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


def Preliminary_analysis_of_metrics(history):
    """
    history: список записей вида [datetime, price, volume], где
             datetime — объект datetime в UTC.
    """

    if not history:
        return 0, 0, 0, 0, None

    history.sort(key=lambda r: r[0])

    now = datetime.now(timezone.utc)
    one_week_ago = now - timedelta(days=7)
    six_month_ago = now - timedelta(days=180)

    total_price = 0.0
    volume = 0
    count = 0
    last_week_records = []

    ts_list = []
    price_list = []
    prices_latest_day = []
    latest_date = None

    for record in history:
        dt = normalize_date(record[0])
        price_i = record[1]
        volume_i = record[2]

        if latest_date is None or dt.date() > latest_date:
            latest_date = dt.date()
            prices_latest_day = [price_i]
        elif dt.date() == latest_date:
            prices_latest_day.append(price_i)

        if dt >= one_week_ago:
            total_price += price_i
            volume += volume_i
            count += 1
            last_week_records.append((dt, price_i, volume_i))

        if dt >= six_month_ago:
            ts = dt.timestamp()
            ts_list.append(ts)
            price_list.append(price_i)

    avg_price_week = total_price / count if count else 0

    sorted_by_price = sorted(last_week_records, key=lambda x: x[1])
    cheapest = sorted_by_price[:3] if len(sorted_by_price) >= 3 else sorted_by_price
    approx_min = sum(r[1] for r in cheapest) / len(cheapest) if cheapest else 0

    most_expensive = sorted_by_price[-3:] if len(sorted_by_price) >= 3 else sorted_by_price
    approx_max = sum(r[1] for r in most_expensive) / len(most_expensive) if most_expensive else 0

    if len(ts_list) < 2 or not prices_latest_day:
        return avg_price_week, volume, approx_max, approx_min, None

    x = np.array(ts_list)
    y = np.array(price_list)
    a, b = np.polyfit(x, y, deg=1)

    current_price = sum(prices_latest_day) / len(prices_latest_day)
    ts_next_month = (now + timedelta(days=30)).timestamp()
    predicted_price_next = a * ts_next_month + b
    percent_change_next_month = ((predicted_price_next - current_price) / current_price) * 100

    return avg_price_week, volume, approx_max, approx_min, float(percent_change_next_month)


def update_data(db: PostgreSQLDB, skin, cookies):
    price_history, skin_orders = get_market_data(skin, db.cursor, cookies)

    db.insert_or_update_orders(skin[0], skin_orders)
    db.update_skin_orders_timestamp(skin[0])
    db.commit()

    db.update_price_history(skin[0], price_history)
    db.update_skin_price_timestamp(skin[0])
    db.commit()

    print("Анализируем предмет и считаем метрики...")
    price, volume, approx_max, approx_min, linreg = Preliminary_analysis_of_metrics(price_history)
    db.update_skins_analysis(skin[0], price, volume, approx_max, approx_min, linreg)
    db.commit()
    return price, volume, approx_max, approx_min, skin_orders, linreg


if __name__ == "__main__":
    model_type = "EVA"
    cookies, driver = authorize_and_get_cookies()
    load_dotenv()

    db = PostgreSQLDB("127.0.0.1", 5432, "steam", "postgres", os.getenv("DEFAULT_PASSWORD"))
    model = PTModel(model_type)

    skins = db.get_filtred_skins()

    for skin in skins:
        # get & update data in db
        price, volume, approx_max, approx_min, skin_orders, linreg = update_data(db, skin, cookies)

        if linreg is None or linreg < 0:
            print(f"Предсказание линейной регрессии для {skin[1]} (ID: {skin[0]}) не удалось или отрицательное.")
            continue
        # model prediction
        y, amount, profit = model.predict(
            price=price,
            volume=volume,
            skin_orders=skin_orders,
            linreg=linreg,
        )

        # buy and log if y is not none
        if y is not None:
            buy_skin(driver, skin[1], y, amount)
            db.insert_log(skin[0], price, amount, profit, model_type)
            db.commit()

    driver.quit()
    db.close()