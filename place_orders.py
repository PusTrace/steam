from datetime import datetime, timedelta, timezone
import os
import numpy as np

# database
from bin.PostgreSQLDB import PostgreSQLDB
# Models
from bin.pt_model import PTModel
# small scripts
from bin.get_order_info import get_orders
from bin.get_history import get_history
from bin.steam import authorize_and_get_cookies, buy_skin


def get_market_data(id, name, orders_timestamp, price_timestamp, cursor, item_name_id, cookies):
    # Проверяем, нужно ли брать новые ордера
    if orders_timestamp is None or orders_timestamp < datetime.now(timezone.utc) - timedelta(days=2):
        item_orders = get_orders(item_name_id)
    else:
        print(f"Используем кэшированные ордера для {name} (ID: {id})")
        cursor.execute("SELECT data FROM orders WHERE skin_id = %s", (id,))
        result = cursor.fetchone()
        if result:
            item_orders = result[0]  # assuming data is in first column
        else:
            item_orders = None

    # Проверяем, нужно ли брать новые цены
    if price_timestamp is None or price_timestamp < datetime.now(timezone.utc) - timedelta(days=2):
        item_price = get_history(name, cookies)
    else:
        print(f"Используем кэшированные цены для {name} (ID: {id})")
        cursor.execute("SELECT date, price, volume FROM pricehistory WHERE skin_id = %s", (id,))
        item_price = cursor.fetchall()

    return item_price, item_orders  # Успешно получили данные — возвращаем


def Preliminary_analysis_of_metrics(history):
    """
    history: список записей вида [date_iso, price, volume], где
             date_iso — ISO-строка в UTC ("YYYY-MM-DDTHH:MM:SSZ" или с +00:00).
    """

    now = datetime.now(timezone.utc)
    one_week_ago = now - timedelta(days=7)
    six_month_ago = now - timedelta(days=180)

    # Переменные для анализа за неделю
    total_price = 0.0
    volume = 0
    count = 0
    last_week_records = []

    # Переменные для годовой регрессии
    ts_list = []
    price_list = []
    dates_all = []

    for record in history:
        raw_date = record[0]
        price_i = record[1]
        volume_i = record[2]

        # Преобразуем дату в UTC-aware datetime
        try:
            dt = datetime.fromisoformat(raw_date.replace('Z', '+00:00'))
        except ValueError:
            dt = datetime.fromisoformat(raw_date)

        # Приводим всё к UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)

        dates_all.append(dt.date())

        if dt >= one_week_ago:
            total_price += price_i
            volume += volume_i
            count += 1
            last_week_records.append((dt, price_i, volume_i))

        if dt >= six_month_ago:
            ts = dt.timestamp()
            ts_list.append(ts)
            price_list.append(price_i)

    # --- Расчёты за неделю ---
    avg_price_week = total_price / count if count else 0

    sorted_by_price = sorted(last_week_records, key=lambda x: x[1])
    cheapest = sorted_by_price[:3] if len(sorted_by_price) >= 3 else sorted_by_price
    approx_min = sum(r[1] for r in cheapest) / len(cheapest) if cheapest else 0

    most_expensive = sorted_by_price[-3:] if len(sorted_by_price) >= 3 else sorted_by_price
    approx_max = sum(r[1] for r in most_expensive) / len(most_expensive) if most_expensive else 0

    if len(ts_list) < 2:
        return avg_price_week, volume, approx_max, approx_min, None

    x = np.array(ts_list)
    y = np.array(price_list)
    a, b = np.polyfit(x, y, deg=1)

    latest_date = max(dates_all)
    prices_latest_day = []

    for record in history:
        raw_date = record[0]
        price_i = record[1]
        try:
            dt = datetime.fromisoformat(raw_date.replace('Z', '+00:00'))
        except ValueError:
            dt = datetime.fromisoformat(raw_date)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)

        if dt.date() == latest_date:
            prices_latest_day.append(price_i)

    if not prices_latest_day:
        return avg_price_week, volume, approx_max, approx_min, None

    current_price = sum(prices_latest_day) / len(prices_latest_day)

    ts_next_month = (now + timedelta(days=30)).timestamp()
    predicted_price_next = a * ts_next_month + b
    percent_change_next_month = ((predicted_price_next - current_price) / current_price) * 100

    return avg_price_week, volume, approx_max, approx_min, float(percent_change_next_month)
    



def update_data(db: PostgreSQLDB, skin, cookies):
    id, name, orders_ts, price_ts, item_name_id = skin
    print(f"Обработка скина: {name} (ID: {id})")

    price_history, skin_orders = get_market_data(id, name, orders_ts, price_ts, db.cursor, item_name_id, cookies)
    
    print("Получены ордера, обновляем базу данных...")
    db.insert_or_update_orders(id, skin_orders)
    db.update_skin_orders_timestamp(id)
    db.commit()

    print("Получена цена, обновляем базу данных...")
    db.update_price_history(id, price_history)
    db.update_skin_price_timestamp(id)
    db.commit()

    print("Анализируем предмет и считаем метрики...")
    price, volume, approx_max, approx_min, linreg = Preliminary_analysis_of_metrics(price_history)
    db.update_skins_analysis(id, price, volume, approx_max, approx_min, linreg)
    db.commit()
    return price, volume, approx_max, approx_min, skin_orders, linreg


if __name__ == "__main__":
    cookies, driver = authorize_and_get_cookies()

    db = PostgreSQLDB("127.0.0.1", 5432, "steam", "pustrace", os.getenv("DEFAULT_PASSWORD"))
    model = PTModel("EVA")
    skins = db.get_filtred_skins()

    for skin in skins:
        # get & update data in db
        price, volume, approx_max, approx_min, skin_orders, linreg = update_data(db, skin, cookies)

        # model prediction
        y, amount, profit = model.predict(price, volume, approx_max, approx_min, skin_orders, linreg)

        # buy and log if y is not none
        if y is not None:
            buy_skin(driver, skin, y, amount)
            db.insert_log(id, price)
            db.commit()

    driver.quit()
    db.close()