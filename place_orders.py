import time
from datetime import datetime, date, timedelta, timezone
import os
import psycopg2
from psycopg2.extras import Json
import numpy as np

from bin.get_order_info import get_orders
from bin.get_history import get_history
from bin.utils import generate_market_url
from bin.steam import authorize_and_get_cookies, buy_skin
from bin.pt_model import PTModel

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


def analyze_orders_weights(
    price: float,
    volume: float,
    approx_max: float,
    approx_min: float,
    skin_orders,
    linreg_change_next_month: float,
    max_multiplier: float = 2.0
):
    """
    Рассчитывает нижний и верхний пороги (threshold_down, threshold_up) с учётом:
      1. Дефолтных коэффициентов: 0.76 (нижний) и 0.86 (верхний).
      2. Истории (linreg_change_next_month) в процентах: оба коэффициента смещаются на линрег.
      3. Приближения (approx_max / approx_min), когда цена ближе к approx_max:
         - Вычисляем вес приближения (approx_weight) в диапазоне [0..1].
         - Добавляем небольшой сдвиг (epsilon) умноженный на этот вес к обоим коэффициентам.
      4. Гарантируем, что оба коэффициента ≥ 0 и ≤ 1 * max_multiplier (чтобы не выйти за разумные пределы).

    После этого проходит фильтрацию заявок (skin_orders), ищет «стенку» и возвращает:
      - False, None, False — если стена не найдена или объём слишком большой.
      - True, candidate_price, approx_true — если найдена «стена» (candidate_price > threshold_down).
    """

    # 1) Базовые коэффициенты (дефолтные «стенки»)
    base_low_coef = 0.76
    base_high_coef = 0.86

    # 2) Применяем историю (linreg_change_next_month может быть отрицательной или положительной)
    low_coef = base_low_coef + linreg_change_next_month/2
    high_coef = base_high_coef + linreg_change_next_month/2


    # 4) Проверяем приближение: учитываем, только если price ближе к approx_max, чем к approx_min
    if approx_max is not None and approx_min is not None and approx_max != approx_min:
        dist_to_max = abs(approx_max - price)
        dist_to_min = abs(approx_min - price)

        if dist_to_max < dist_to_min:
            total_span = abs(approx_max - approx_min)
            raw_weight = 1.0 - (dist_to_max / total_span)  # в [0..1], где 1 — цена ровно = approx_max
            approx_weight = max(0.0, min(1.0, raw_weight))

            # Небольшой сдвиг: допустим, ε = 0.02 (2%)
            epsilon = 0.02
            shift = approx_weight * epsilon

            low_coef += shift
            high_coef += shift


    # 6) Переводим коэффициенты в абсолютные цены-пороги
    threshold_down = price * low_coef
    threshold_up = price * high_coef


    base_wall_qty_threshold = volume * 0.1

    # Быстрая проверка: если есть крупный объём внутри «стенки» — сразу бьём в отказ
    fast_check_volume = 0.0
    for i in range(len(skin_orders) - 1):
        price_high = skin_orders[i][0]
        price_low = skin_orders[i + 1][0]
        if price_high > threshold_up > price_low:
            fast_check_volume = skin_orders[i + 1][1]
            break  # достаточно найти один такой уровень
    if fast_check_volume > (volume * 1.2) / 7:
        return False, None
    else:
        # Преобразуем агрегированные количества в «эффективные» (effective_qty)
        effective_orders = []
        for i, order in enumerate(skin_orders):
            price_level, aggregated_qty, useless_information = order
            if i == 0:
                effective_qty = aggregated_qty
            else:
                effective_qty = aggregated_qty - skin_orders[i - 1][1]
            effective_orders.append((price_level, effective_qty))

        # Фильтруем только те уровни, что внутри [threshold_down, threshold_up]
        filtered_orders = [
            (p, q) for p, q in effective_orders
            if threshold_down < p <= threshold_up
        ]
        filtered_orders.sort(key=lambda x: x[0])

        candidate_price = round(threshold_down, 2)

        for price_level, effective_qty in filtered_orders:
            if price_level <= candidate_price:
                print(f"{price_level:.2f} <= {candidate_price:.2f}, пропускаем.")
                continue

            # Расчитываем динамический порог для объёма «стены»
            multiplier = 1 + (max_multiplier - 1) * ((price_level - threshold_down) / (threshold_up - threshold_down))
            dynamic_threshold = base_wall_qty_threshold * multiplier

            if effective_qty >= dynamic_threshold:
                candidate_price = price_level + 0.1
                print(
                    f"Ордер на {price_level:.2f} (qty={effective_qty:.2f}) прошёл порог "
                    f"{dynamic_threshold:.2f}. Новая candidate_price = {candidate_price:.2f}"
                )
            else:
                print(
                    f"Ордер на {price_level:.2f} (qty={effective_qty:.2f}) не прошёл порог "
                    f"{dynamic_threshold:.2f}."
                )

        if candidate_price >= threshold_up:
            return False, None

        return True, candidate_price


def analyze_metrix(history):
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
    

class PostgreSQLDB:
    def __init__(self, host, port, dbname, user, password):
        self.conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password
        )
        self.cursor = self.conn.cursor()

    def insert_or_update_orders(self, skin_id, skin_orders):
        self.cursor.execute("""
            INSERT INTO orders (skin_id, data)
            VALUES (%s, %s)
            ON CONFLICT (skin_id) DO UPDATE
            SET data = EXCLUDED.data
        """, (skin_id, Json(skin_orders)))

    def update_skin_orders_timestamp(self, skin_id):
        self.cursor.execute("""
            UPDATE skins
            SET orders_timestamp = %s
            WHERE id = %s
        """, (datetime.now().isoformat(), skin_id))

    def update_skin_price_timestamp(self, skin_id):
        self.cursor.execute("""
            UPDATE skins
            SET price_timestamp = %s
            WHERE id = %s
        """, (datetime.now().isoformat(), skin_id))

    def update_price_history(self, skin_id, price_history):
        # Получаем уже существующие даты для этого skin_id
        self.cursor.execute("""
            SELECT date FROM pricehistory WHERE skin_id = %s
        """, (skin_id,))
        existing_dates = set(row[0] for row in self.cursor.fetchall())

        to_insert = []

        for record in price_history:
            date_str, price, volume = record
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))

            # Вставляем только если ещё не существует
            if dt not in existing_dates:
                to_insert.append((skin_id, dt, price, volume))

        # Массовая вставка новых записей
        if to_insert:
            self.cursor.executemany("""
                INSERT INTO pricehistory (skin_id, date, price, volume)
                VALUES (%s, %s, %s, %s)
            """, to_insert)


    def update_skins_analysis(self, id, price, volume, approx_max, approx_min, linreg_change):
        self.cursor.execute("""
            UPDATE skins
            SET price = %s,
                volume = %s,
                approx_max = %s,
                approx_min = %s,
                analysis_timestamp = %s,
                linreg_change_next_month = %s
            WHERE id = %s
        """, (price, volume, approx_max, approx_min, datetime.now().isoformat(), linreg_change, id))

    def insert_log(self, skin_id, price):
        self.cursor.execute("""
            INSERT INTO logs (skin_id, event_type, event_time, price, quantity)
            VALUES (%s, %s, %s, %s, %s)
        """, (skin_id, "buy", datetime.now().isoformat(), price, 1))

    def commit(self):
        self.conn.commit()

    def close(self):
        self.cursor.close()
        self.conn.close()
        
    def get_skins_to_update(self):
        self.cursor.execute(
            """
            SELECT id, name, orders_timestamp, price_timestamp, item_name_id
            FROM skins
            WHERE 
                price_timestamp IS NULL
                AND item_name_id IS NOT NULL
            """,
        )
        return self.cursor.fetchall()



def analyze_skin(db: PostgreSQLDB, skin, cookies):
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
    price, volume, approx_max, approx_min, linreg = analyze_metrix(price_history)
    db.update_skins_analysis(id, price, volume, approx_max, approx_min, linreg)
    db.commit()
    return price, volume, approx_max, approx_min, skin_orders, linreg


if __name__ == "__main__":
    cookies, driver = authorize_and_get_cookies()

    db = PostgreSQLDB("localhost", 5432, "steam", "pustrace", os.getenv("DEFAULT_PASSWORD"))
    model = PTModel("EVA")
    skins = db.get_skins_to_update()

    for skin in skins:
        price, volume, approx_max, approx_min, skin_orders, linreg = analyze_skin(db, skin, cookies)
        model.init(price, volume, approx_max, approx_min, skin_orders, linreg)
        y = model.predict(skin_orders)
        buy_skin(driver, skin, y)
        db.insert_log(id, price)
        db.commit()

    driver.quit()
    db.close()