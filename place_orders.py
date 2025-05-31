from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
import time
from datetime import datetime, date, timedelta, timezone
import os
import psycopg2
from psycopg2.extras import Json
import numpy as np
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException
from selenium_stealth import stealth
from webdriver_manager.chrome import ChromeDriverManager
from bin.get_order_info import get_orders
from bin.get_history import get_history
from bin.utils import generate_market_url

def get_market_data(id, name, orders_timestamp, price_timestamp, cursor, item_name_id, cookies):
    # Проверяем, нужно ли брать новые ордера
    if orders_timestamp is None or orders_timestamp < date.today() - timedelta(days=1):
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
    if price_timestamp is None or price_timestamp < date.today() - timedelta(days=1):
        item_price = get_history(name, cookies)
    else:
        print(f"Используем кэшированные цены для {name} (ID: {id})")
        cursor.execute("SELECT date, price, volume FROM pricehistory WHERE skin_id = %s", (id,))
        item_price = cursor.fetchall()

    return item_price, item_orders  # Успешно получили данные — возвращаем


def steam_login(driver):
    login_url = "https://steamcommunity.com/login/home/"
    driver.get(login_url)
    
    # Ожидаем появления элемента, свидетельствующего об успешном входе (например, имя пользователя)
    WebDriverWait(driver, 99999999999).until(
        EC.presence_of_element_located((By.CLASS_NAME, "actual_persona_name"))
    )
    print("Авторизация в Steam выполнена.")
def setup_driver(headless=True):
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
    else:
        options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    # Применяем настройки stealth для обхода антибот-защиты
    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True)
    return driver

def load_cookies(driver, cookies):
    """Загружает cookies в драйвер."""
    driver.get("https://steamcommunity.com/")
    for cookie in cookies:
        # Удаляем поле 'expiry', если оно присутствует, чтобы не возникло ошибок
        if 'expiry' in cookie:
            cookie.pop('expiry')
        driver.add_cookie(cookie)
    driver.refresh()
    
def buy_skin(driver, url, order_price, weight_number_of_items):
    wait = WebDriverWait(driver, 10)
    driver.get(url)
    try:
        btn_place_order = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "#market_buyorder_info > div:nth-child(1) > div:nth-child(1) > a > span")
        ))
        driver.execute_script("arguments[0].scrollIntoView();", btn_place_order)
        ActionChains(driver).move_to_element(btn_place_order).perform()
        btn_place_order.click()
        
        price_for_skin = wait.until(EC.presence_of_element_located(
            (By.ID, "market_buy_commodity_input_price")
        ))
        driver.execute_script("arguments[0].scrollIntoView();", price_for_skin)
        ActionChains(driver).move_to_element(price_for_skin).perform()
        price_for_skin.clear()
        price_for_skin.send_keys(order_price)
        time.sleep(0.5)
        
        item_quantity = wait.until(EC.presence_of_element_located(
            (By.ID, "market_buy_commodity_input_quantity")
        ))
        item_quantity.clear()
        item_quantity.send_keys(weight_number_of_items)
        time.sleep(0.5)
        
        ssa_input = wait.until(EC.presence_of_element_located(
            (By.ID, "market_buyorder_dialog_accept_ssa")
        ))
        ssa_input.click()
        time.sleep(0.5)
        
        btn_to_complite = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "#market_buyorder_dialog_purchase > span")
        ))
        time.sleep(0.5)
        btn_to_complite.click()
        time.sleep(2.5)
    except TimeoutException:
        print("Timeout: Элементы не найдены")
        return
    except Exception as e:
        print("Ошибка:", e)
        driver.quit()

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
            price_level, aggregated_qty = order
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




def analyze_price(history):
    """
    history: список записей вида [date_iso, price, volume], где
             date_iso может быть либо "YYYY-MM-DDTHH:MM:SSZ", 
             либо "YYYY-MM-DD HH:MM:SS+03" (PostgreSQL-style).
    """
    # 1) Определим «сейчас» в UTC
    now = datetime.now(timezone.utc)
    one_week_ago = now - timedelta(days=7)
    one_year_ago = now - timedelta(days=365)

    # Переменные для недели
    total_price = 0.0
    volume = 0
    count = 0
    last_week_records = []

    # Переменные для года (регрессия)
    ts_list = []
    price_list = []

    # Буфер для поиска «последнего дня» среди всех записей
    # (считаем дату без учёта времени, просто date())
    dates_all = []

    # 2) Пройдём по всем записям history
    for record in history:
        raw_date = record[0]
        price_i = record[1]
        volume_i = record[2]

        # Попробуем распарсить дату — она может быть в ISO с 'Z' или с таймзоной +03
        try:
            # Если формат "YYYY-MM-DDTHH:MM:SSZ" или похожий
            dt = datetime.fromisoformat(raw_date.replace('Z', '+00:00'))
        except ValueError:
            # Если формат "YYYY-MM-DD HH:MM:SS+03"
            dt = datetime.fromisoformat(raw_date)

        # Сохраняем дату (без времени) для вычисления «последнего дня»
        dates_all.append(dt.date())

        # --- Сбор данных за неделю ---
        if dt >= one_week_ago:
            total_price += price_i
            volume += volume_i
            count += 1
            last_week_records.append((dt, price_i, volume_i))

        # --- Сбор данных за год для регрессии ---
        if dt >= one_year_ago:
            ts = dt.timestamp()
            ts_list.append(ts)
            price_list.append(price_i)

    # 3) Проверка: есть ли вообще данные за последнюю неделю?
    if count == 0:
        print("Нет данных за последнюю неделю.")
        return

    # --- 4) Подсчёт показателей за неделю ---
    avg_price_week = total_price / count

    # Сортируем last_week_records по цене (индекс 1)
    sorted_by_price = sorted(last_week_records, key=lambda x: x[1])

    # Три самых дешёвых: берем первые три цены
    cheapest = sorted_by_price[:3]
    approx_min = sum(r[1] for r in cheapest) / len(cheapest)

    # Три самых дорогих: берём последние три цены
    most_expensive = sorted_by_price[-3:]
    approx_max = sum(r[1] for r in most_expensive) / len(most_expensive)

    # --- 5) Строим регрессию за год (если точек >= 2) ---
    if len(ts_list) < 2:
        print("Недостаточно точек за год для построения регрессии.")
        # Вместо прогноза возвращаем None
        return avg_price_week, volume, approx_max, approx_min, None

    x = np.array(ts_list)
    y = np.array(price_list)
    a, b = np.polyfit(x, y, deg=1)

    # --- 6) Вычисляем «текущую цену» как среднее за самый последний день в history ---
    # Находим дату (date) максимального дня
    latest_date = max(dates_all)

    # Берём все записи из history, у которых dt.date() == latest_date
    prices_latest_day = []
    for record in history:
        raw_date = record[0]
        price_i = record[1]
        try:
            dt = datetime.fromisoformat(raw_date.replace('Z', '+00:00'))
        except ValueError:
            dt = datetime.fromisoformat(raw_date)
        if dt.date() == latest_date:
            prices_latest_day.append(price_i)

    # Если вдруг что-то пошло не так (хотя маловероятно)
    if not prices_latest_day:
        print("Не получилось вычислить последние данные за день.")
        return avg_price_week, volume, approx_max, approx_min, None

    current_price = sum(prices_latest_day) / len(prices_latest_day)

    # --- 7) Прогноз цены через месяц (приближённо +30 дней) ---
    one_month_ahead = now + timedelta(days=30)
    ts_next_month = one_month_ahead.timestamp()
    predicted_price_next = a * ts_next_month + b

    # Процентное изменение относительно current_price
    percent_change_next_month = ((predicted_price_next - current_price) / current_price) * 100
    float(percent_change_next_month)
    # --- 8) Возвращаем всё, что попросили ---
    return avg_price_week, volume, approx_max, approx_min, percent_change_next_month


def authorize_and_get_cookies():
    driver_normal = setup_driver(headless=False)
    steam_login(driver_normal)
    cookies = driver_normal.get_cookies()
    driver_normal.quit()
    driver_headless = setup_driver(headless=True)
    load_cookies(driver_headless, cookies)
    return cookies, driver_headless


def connect_db():
    """Подключение к базе данных PostgreSQL."""
    return psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="steam",
        user="pustrace",
        password=os.getenv("DEFAULT_PASSWORD")
    )
    
def get_skins_to_update(cursor):
    cursor.execute(
        """
        SELECT id, name, orders_timestamp, price_timestamp, item_name_id
        FROM skins
        WHERE 
            (DATE(price_timestamp) IS DISTINCT FROM %s OR DATE(orders_timestamp) IS DISTINCT FROM %s)
            AND item_name_id IS NOT NULL
        """,
        (date.today(), date.today())
    )
    return cursor.fetchall()


def process_skin(cursor, driver_headless, skin, cookies):
    id, name, orders_timestamp, price_timestamp, item_name_id = skin
    print(f"Обработка скина: {name} (ID: {id})")
    price_history, skin_orders = get_market_data(id, name, orders_timestamp, price_timestamp, cursor, item_name_id, cookies)

    cursor.execute("""
        INSERT INTO orders (skin_id, data)
        VALUES (%s, %s)
        ON CONFLICT (skin_id) DO UPDATE
        SET data = EXCLUDED.data
    """, (id, Json(skin_orders)))
    conn.commit()
    
    cursor.execute("""
        UPDATE skins
        SET orders_timestamp = %s
        WHERE id = %s
    """, (datetime.now().isoformat(), id))
    conn.commit()
    print("Анализируем историю цен...")
    for record in price_history:
        date_str, price, volume = record
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        hour = dt.hour

        # Проверяем наличие записи
        cursor.execute("""
            SELECT 1 FROM pricehistory WHERE skin_id = %s AND date = %s
        """, (id, dt))
        exists = cursor.fetchone()

        if exists:
            if hour == 0:
                # Обновляем цену и объём, если час = 0 (и дата уже есть)
                cursor.execute("""
                    UPDATE pricehistory
                    SET price = %s, volume = %s
                    WHERE skin_id = %s AND date = %s
                """, (price, volume, id, dt))
        else:
            # Если записи с такой датой нет
            if hour == 0:
                # Удаляем существующую запись с этой датой, если час = 0
                cursor.execute("""
                    DELETE FROM pricehistory WHERE skin_id = %s AND date::date = %s::date
                """, (id, dt))
            # Вставляем новую запись в любом случае, если даты нет
            cursor.execute("""
                INSERT INTO pricehistory (skin_id, date, price, volume)
                VALUES (%s, %s, %s, %s)
            """, (id, dt, price, volume))
    conn.commit()
    
    cursor.execute("""
        UPDATE skins
        SET price_timestamp = %s
        WHERE id = %s
    """, (datetime.now().isoformat(), id))
    conn.commit()

    print("Анализируем цену и считаем метрики...")
    price, volume, approx_max, approx_min, linreg_change_next_month = analyze_price(price_history)

    cursor.execute("""
        INSERT INTO skins (id, price, volume, approx_max, approx_min, analysis_timestamp, linreg_change_next_month)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE
        SET price = EXCLUDED.price, volume = EXCLUDED.volume, approx_max = EXCLUDED.approx_max, approx_min = EXCLUDED.approx_min, analysis_timestamp = EXCLUDED.analysis_timestamp, linreg_change_next_month = EXCLUDED.linreg_change_next_month
    """, (id, price, volume, approx_max, approx_min, datetime.now().isoformat(), linreg_change_next_month))
    conn.commit()

    decision, order_price = analyze_orders_weights(price, volume, approx_max, approx_min, skin_orders, linreg_change_next_month)

    if decision:
        print(f"Решение: купить скин {name} (ID: {id}) по цене {order_price:.2f}")
        url = generate_market_url(name)
        buy_skin(driver_headless, url, order_price, 1)

        cursor.execute("""
            INSERT INTO logs (skin_id, event_type, event_time, price, quantity)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            id,
            "buy",
            datetime.now().isoformat(),
            order_price,
            1
        ))
        conn.commit()
    else:
        print(f"Решение: не покупать скин {name} (ID: {id}), цена {order_price:.2f} ниже порога.")

    time.sleep(3.5)

    print("Orders placement complete.")
    driver_headless.quit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    cookies, driver = authorize_and_get_cookies()

    conn = connect_db()
    cursor = conn.cursor()

    skins = get_skins_to_update(cursor)

    for skin in skins:
        process_skin(cursor, driver, skin, cookies)
        time.sleep(3.5)

    driver.quit()
    conn.close()