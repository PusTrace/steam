from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
import time
from datetime import datetime, date
import json
import signal
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from selenium_stealth import stealth
from webdriver_manager.chrome import ChromeDriverManager
import sys
import os
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
from utils.utils import save_data, signal_handler, generate_market_url
from orders.get_order_info import get_orders
from price.get_steam_price import get_steam_price

def get_market_data(skin, skin_id, timestamp_orders, timestamp_price):
    today = date.today()  # Пример формата 'YYYY-MM-DD'
    
    # Проверяем, если ордеры уже получены сегодня, читаем их из файла
    item_orders = None
    if timestamp_orders == today:
        print(f"Пропускаем {skin}, ордера уже были получены сегодня. Чтение из JSON.")
        with open("/home/pustrace/programming/trade/steam/database/orders.json", "r", encoding="utf-8") as f:
            orders_data = json.load(f)
        item_orders = orders_data.get(skin)
    
    # Проверяем, если цена уже получена сегодня, читаем её из файла
    item_price = None
    if timestamp_price == today:
        print(f"Пропускаем {skin}, цена была получена сегодня. Чтение из JSON.")
        with open("/home/pustrace/programming/trade/steam/database/database.json", "r", encoding="utf-8") as f:
            price_data = json.load(f)
        item_price = price_data.get(skin)
    
    errors = 0
    while errors < 6:
        # Если данные ордеров отсутствуют, запрашиваем их
        if not item_orders:
            item_orders = get_orders(skin_id)
            if item_orders:
                # Обновляем JSON-файл с ордерами
                save_data({skin: item_orders}, "/home/pustrace/programming/trade/steam/database/orders.json")
                errors = 0
                time.sleep(3.5)
            else:
                errors += 1
                if errors >= 6:
                    print("Превышено количество ошибок 429 подряд. Остановка на час.")
                    time.sleep(60*60)
                time.sleep(40)
        
        # Если данные цены отсутствуют, запрашиваем их
        if not item_price:
            item_price = get_steam_price(skin)
            if item_price:
                # Обновляем JSON-файл с ценами
                save_data({skin: item_price}, "/home/pustrace/programming/trade/steam/database/database.json")
                errors = 0
                time.sleep(3.5)
            else:
                errors += 1
                if errors >= 6:
                    print("Превышено количество ошибок 429 подряд. Остановка на час.")
                    time.sleep(60*60)
                time.sleep(40)
        
        if item_price and item_orders:
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

def analyze_orders_weights(price, orders, approx_price):
    median_price_str = price.get("median_price")
    lowest_price_str = price.get("lowest_price")
    volume_str = price.get("volume")
    volume = int(volume_str.replace(",", "").strip())
    
    # Обработка цен
    if median_price_str is not None:
        median_price = float(median_price_str.replace("₸", "").replace(",", ".").replace(" ", "").strip())
    else:
        median_price = None
        
    if lowest_price_str is not None:
        lowest_price = float(lowest_price_str.replace("₸", "").replace(",", ".").replace(" ", "").strip())
    else:
        lowest_price = None

    if median_price is None:
        median_price = lowest_price
    if lowest_price is None:
        lowest_price = median_price

    buy_order_graph = orders.get("buy_order_graph", [])
    
    active_check_orders = 0
    max_multiplier = 2
    current_price = median_price if median_price is not None else lowest_price

    # Установка пороговых значений
    if approx_price is not None:
        threshold_down = approx_price * 0.87
        threshold_up = approx_price * 0.97
    else:
        threshold_down = current_price * 0.74
        threshold_up = current_price * 0.84

    base_wall_qty_threshold = volume * 0.1

    for i in range(len(buy_order_graph) - 1):
        price_high = buy_order_graph[i][0]
        price_low = buy_order_graph[i+1][0]
        if price_high > threshold_up > price_low:
            active_check_orders = buy_order_graph[i+1][1]
    if active_check_orders > volume * 2.5:
        logs[skin] = {"active_check_orders > volume*2.5": [active_check_orders, volume],
                      "timestamp_skip": datetime.now().isoformat()}
        return False, None

    # Корректный расчёт "эффективного" количества ордеров
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
        return False, None

    return True, candidate_price




if __name__ == "__main__":


    # Регистрируем обработчик сигнала (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)
    
    # 1. Запуск драйвера в обычном режиме для логина
    driver_normal = setup_driver(headless=False)
    steam_login(driver_normal)
    cookies = driver_normal.get_cookies()
    driver_normal.quit()  # Закрываем обычный браузер
    driver_headless = setup_driver(headless=True)
    load_cookies(driver_headless, cookies)

    with open("/home/pustrace/programming/trade/steam/database/logs.json", "r") as file:
        logs = json.load(file)
    with open("/home/pustrace/programming/trade/steam/database/perfect.json", "r") as file:
        perfect = json.load(file)
    with open ("/home/pustrace/programming/trade/steam/database/item_nameids.json", "r", encoding="utf-8") as f:
        item_nameids = json.load(f)
    with open ("/home/pustrace/programming/trade/steam/database/orders.json", "r") as file:
        all_orders = json.load(file)
    with open ("/home/pustrace/programming/trade/steam/database/database.json", "r") as file:
        database = json.load(file)
    

    consecutive_errors = 0
    max_attempts = 6
    passive_check_orders = 0


    for skin, data in sorted(perfect.items(), key=lambda x: x[1].get("weight_of_items", 0), reverse=True):
        if skin in logs: 
            print (f"Orders is exists for {skin}")
            continue
        approx_min = data.get("approx_min")
        approx_max = data.get("approx_max")
        median_price = data.get("median_price")
        lowest_price = data.get("lowest_price")
        volume = data.get("volume")
        weight_number_of_items = data.get("weight_number_of_items")
        approx_price = None
        if approx_min is None or approx_max is None:
            print(f"Не удалось получить данные о цене для '{skin}'")
        
        if median_price is not None or median_price < lowest_price:
            current_price_pass = median_price
        else:
            current_price_pass = lowest_price
        
        if (approx_max - approx_min) > current_price_pass*0.2:
            approx_price = approx_min
            logs[skin] = {"approx": [approx_max, approx_price, approx_max-approx_min]}
            save_data(logs, "/home/pustrace/programming/trade/steam/database/logs.json")
        
        if skin in item_nameids:
            skin_id = item_nameids[skin]
        if skin in logs:
            print(f"Логи для '{skin}' уже существуют")
            continue
        
        if skin in all_orders:
            date_orders = all_orders[skin].get("timestamp_orders")
            timestamp_orders = datetime.fromisoformat(date_orders).date()
        if skin in database:
            date_price = database[skin].get("timestamp")    
            timestamp_price = datetime.fromisoformat(date_price).date()
        
        print(f"Получение данных для '{skin}' .")
        price, skin_orders = get_market_data(skin, skin_id, timestamp_orders, timestamp_price)
        
        decision, order_price = analyze_orders_weights(price, skin_orders, approx_price)
        
        # Buy logic
        if decision:
            url = generate_market_url(skin)
            weight_number_of_items = round(int(weight_number_of_items), 0)
            buy_skin(driver_headless, url, order_price, weight_number_of_items)
            logs[skin] = {"order_price": order_price,
                            "weight_number_of_items": weight_number_of_items,
                            "url": url,
                            "timestamp": datetime.now().isoformat()}
            save_data(logs, "/home/pustrace/programming/trade/steam/database/logs.json")
    
    
    print("Выставление ордеров завершено.")
    driver_headless.quit()
