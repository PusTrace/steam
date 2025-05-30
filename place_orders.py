from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
import time
from datetime import datetime, date, timedelta, timezone
import os
import psycopg2
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException
from selenium_stealth import stealth
from webdriver_manager.chrome import ChromeDriverManager
from bin.get_order_info import get_orders
from bin.get_history import get_history
from bin.tornet import change_ip
from bin.utils import generate_market_url

def get_market_data(id, skin_name, timestamp_orders, timestamp_price, skin_id, cursor):

    errors = 0
    while errors < 6:
        try:
            # Проверяем, нужно ли брать новые ордера
            if timestamp_orders is None or timestamp_orders < date.today() - timedelta(days=1):
                item_orders = get_orders(skin_id)
            else:
                cursor.execute("SELECT data FROM orders WHERE skin_id = %s", (id,))
                result = cursor.fetchone()
                if result:
                    item_orders = result[0]  # assuming data is in first column
                else:
                    item_orders = None

            # Проверяем, нужно ли брать новые цены
            if timestamp_price is None or timestamp_price < date.today() - timedelta(days=1):
                item_price = get_history(skin_name)
            else:
                cursor.execute("SELECT date, price, volume FROM pricehistory WHERE skin_id = %s", (id,))
                item_price = cursor.fetchall()

            return item_price, item_orders  # Успешно получили данные — возвращаем

        except Exception as e:
            print("Ошибка при получении данных:", e)
            errors += 1
            if errors >= 2:
                print("Превышено количество ошибок, меняем IP.")
                change_ip()
            time.sleep(20)
        return item_price, item_orders

        
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

def analyze_orders_weights(price, volume, approx_max, approx_min, skin_orders):

    approx_true = False

    buy_order_graph = orders.get("buy_order_graph", [])
    
    active_check_orders = 0
    max_multiplier = 2

    # Установка пороговых значений
    if price is not None:
        threshold_down = price * 0.83
        threshold_up = price * 0.94
        approx_true = True
    else:
        threshold_down = price * 0.74
        threshold_up = price * 0.84

    base_wall_qty_threshold = volume * 0.1

    for i in range(len(buy_order_graph) - 1):
        price_high = buy_order_graph[i][0]
        price_low = buy_order_graph[i+1][0]
        if price_high > threshold_up > price_low:
            active_check_orders = buy_order_graph[i+1][1]
    if active_check_orders > volume * 1.2:
        return False, None, False
    else:
        effective_orders = []
        for i, order in enumerate(buy_order_graph):
            price_level = order[0]
            aggregated_qty = order[1]
            if i == 0:
                effective_qty = aggregated_qty
            else:
                effective_qty = aggregated_qty - buy_order_graph[i-1][1]
            effective_orders.append((price_level, effective_qty))

        # Фильтруем ордера по порогам
        filtered_orders = [(p, q) for p, q in effective_orders if threshold_down < p <= threshold_up]
        filtered_orders.sort(key=lambda x: x[0])

        candidate_price = round(threshold_down, 2)
        print(f"Начинаем с candidate_price = {candidate_price:.2f}")

        for price_level, effective_qty in filtered_orders:
            if price_level <= candidate_price:
                print(f"{price_level} <= {candidate_price}")
                continue

            multiplier = 1 + (max_multiplier - 1) * ((price_level - threshold_down) / (threshold_up - threshold_down))
            dynamic_threshold = base_wall_qty_threshold * multiplier

            if effective_qty >= dynamic_threshold:
                candidate_price = price_level + 0.01
                print(f"Оrдер на {price_level:.2f} с эффективным количеством {effective_qty:.2f} (порог {dynamic_threshold:.2f}) "
                    f"считается стенкой. Новая candidate_price = {candidate_price:.2f}")
            else:
                print(f"Оrдер на {price_level:.2f} с эффективным количеством {effective_qty:.2f} не прошёл проверку (требуется {dynamic_threshold:.2f}).")
        if candidate_price >= threshold_up:
            logs[skin] = {"candidate_price >= threshold_up": [candidate_price, threshold_up],
                        "timestamp_skip": datetime.now().isoformat()}
            return False, None, False
        
        return True, candidate_price, approx_true

def analyze_price(history):
    now = datetime.now(timezone.utc)
    one_week_ago = now - timedelta(days=7)

    total_price = 0.0
    volume = 0
    count = 0

    last_week_records = []

    for record in history:
        dt = datetime.fromisoformat(record[0].replace('Z', '+00:00'))
        if dt >= one_week_ago:
            _price = record[1]
            _volume = record[2]
            total_price += _price
            volume += _volume
            count += 1
            last_week_records.append(record)

    if count == 0:
        print("Нет данных за последнюю неделю.")
        return

    price = total_price / count

    # Сортировка по цене
    sorted_by_price = sorted(last_week_records, key=lambda x: x[1])

    # 3 самых дешёвых
    cheapest = sorted_by_price[:3]
    approx_min = sum([r[1] for r in cheapest]) / len(cheapest)

    # 3 самых дорогих
    most_expensive = sorted_by_price[-3:]
    approx_max = sum([r[1] for r in most_expensive]) / len(most_expensive)
    
    return price, volume, approx_max, approx_min



if __name__ == "__main__":
    # Запуск драйвера для логина и получения cookies
    driver_normal = setup_driver(headless=False)
    steam_login(driver_normal)
    cookies = driver_normal.get_cookies()
    driver_normal.quit()
    driver_headless = setup_driver(headless=True)
    load_cookies(driver_headless, cookies)

    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="steam",
        user="pustrace",
        password=os.getenv("DEFAULT_PASSWORD")
    )
    cursor = conn.cursor()

    # Получаем все скины из таблицы skins
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
    skins_data = cursor.fetchall()

    for id, name, orders_timestamp, price_timestamp, item_name_id in skins_data:
        print(f"Fetching market data for '{name}'...")
        price_history, skin_orders = get_market_data(id, name, orders_timestamp, price_timestamp, cursor, item_name_id)

        cursor.execute("""
            INSERT INTO orders (id, data, skin_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (id) DO UPDATE
            SET skin_orders = EXCLUDED.skin_orders
        """, (id, skin_orders, name))
        conn.commit()
        
        cursor.execute("""
            INSERT INTO skins (id, orders_timestamp)
            VALUES (%s, %s)
            ON CONFLICT (id) DO UPDATE
            SET orders_timestamp = EXCLUDED.orders_timestamp
        """, (id, datetime.now().isoformat()))
        conn.commit()
        
        for record in price_history:
            date_str, price, volume = record
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            hour = dt.hour

            # Проверяем наличие записи
            cursor.execute("""
                SELECT 1 FROM pricehistory WHERE id = %s AND date = %s
            """, (id, dt))
            exists = cursor.fetchone()

            if exists:
                if hour == 0:
                    # Обновляем цену и объём, если час = 0 (и дата уже есть)
                    cursor.execute("""
                        UPDATE pricehistory
                        SET price = %s, volume = %s
                        WHERE id = %s AND date = %s
                    """, (price, volume, id, dt))
            else:
                # Если записи с такой датой нет
                if hour == 0:
                    # Удаляем существующую запись с этой датой, если час = 0
                    cursor.execute("""
                        DELETE FROM pricehistory WHERE id = %s AND date::date = %s::date
                    """, (id, dt))
                # Вставляем новую запись в любом случае, если даты нет
                cursor.execute("""
                    INSERT INTO pricehistory (id, date, price, volume)
                    VALUES (%s, %s, %s, %s)
                """, (id, dt, price, volume))
        conn.commit()
        
        cursor.execute("""
            INSERT INTO skins (id, price_timestamp)
            VALUES (%s, %s)
            ON CONFLICT (id) DO UPDATE
            SET price_timestamp = EXCLUDED.price_timestamp
        """, (id, datetime.now().isoformat()))
        conn.commit()
        
        # Анализируем цену
        price, volume, approx_max, approx_min = analyze_price(price_history)
        
        cursor.execute("""
            INSERT INTO skins (id, price, volume, approx_max, approx_min, analysis_timestamp)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE
            SET price = EXCLUDED.price, volume = EXCLUDED.volume, approx_max = EXCLUDED.approx_max, approx_min = EXCLUDED.approx_min, analysis_timestamp = EXCLUDED.analysis_timestamp
        """, (id, price, volume, approx_max, approx_min, datetime.now().isoformat()))
        conn.commit()

        decision, order_price, approx_true = analyze_orders_weights(price, volume, approx_max, approx_min, skin_orders)

        if decision:
            url = generate_market_url(name)
            weight_number_of_items = round(int(skin_orders.get("weight_number_of_items", 0)), 0)
            buy_skin(driver_headless, url, order_price, weight_number_of_items)

            # Сохраняем логи в базу (аналог logs[skin] = {...})
            cursor.execute("""
                INSERT INTO logs (skin_name, order_price, approx_difference, weight_number_of_items, url, timestamp)
                VALUES (%s, %s, %s, %s, %s, now())
            """, (
                name,
                order_price,
                (price.get("approx_max", 0) - price.get("approx_min", 0)) if approx_true else None,
                weight_number_of_items,
                url
            ))
            conn.commit()

        time.sleep(3.5)

    print("Orders placement complete.")
    driver_headless.quit()
    cursor.close()
    conn.close()