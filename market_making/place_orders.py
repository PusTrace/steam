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
    
    WebDriverWait(driver, 99999999999).until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[7]/div[7]/div[1]/div[1]/div/div/div/div[1]/div[1]/span[1]")))
    print("Авторизация в Steam выполнена.")
    
def buy_skin(driver, url, order_price, weight_number_of_items):
    wait = WebDriverWait(driver, 10)  # Ожидание до 10 секунд
    driver.get(url)
    try:
        btn_place_order = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#market_buyorder_info > div.sih_market_buyorder_info__wrapper > div:nth-child(1) > div > div.column.items-end.gap-5 > div.row.gap-10.order-control__row-btn > a.order-control__show-tooltip-btn.order-control__btn.sih_button.sih_pre_shadow_button.h-32.box-shadow-45 > span")
            ))
        driver.execute_script("arguments[0].scrollIntoView();", btn_place_order)
        ActionChains(driver).move_to_element(btn_place_order).perform()
        btn_place_order.click()
        price_for_skin = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#sih-order-buy-price")
            ))
        driver.execute_script("arguments[0].scrollIntoView();", price_for_skin)
        ActionChains(driver).move_to_element(price_for_skin).perform()
        price_for_skin.send_keys(order_price)
        time.sleep(0.5)
        price_for_skin.send_keys(Keys.RETURN)
        time.sleep(0.5)
        btn_to_complite =wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "#market_buyorder_info > div.sih_market_buyorder_info__wrapper > div:nth-child(1) > div > div.order-control__tooltip.buy-order-tooltip > div > div.row.items-center.gap-12 > div > a")
            ))
        driver.execute_script("arguments[0].scrollIntoView();", btn_to_complite)
        ActionChains(driver).move_to_element(btn_to_complite).perform()
        btn_to_complite.click()
    except TimeoutException:
        return
    except Exception as e:
        driver.quit()

def analyze_orders_weights(price, orders):
    median_price = price.get("median_price")
    lowest_price = price.get("lowest_price")
    volume = price.get("volume")
    # Извлекаем агрегированные ордера; каждый ордер имеет вид: [price, aggregated_quantity, ...]
    buy_order_graph = orders.get("buy_order_graph", [])
    
    passive_check_orders = 0

    max_multiplier = 2  # Максимальный коэффициент увеличения цены для стенки
    current_price = median_price if median_price is not None else lowest_price

    # Пороговые значения
    threshold_74 = current_price * 0.74
    threshold_82 = current_price * 0.82
    base_wall_qty_threshold = volume * 0.1
    for i in range(len(buy_order_graph) - 1):
        price_high = buy_order_graph[i][0]
        price_low = buy_order_graph[i+1][0]
        if price_high > threshold_82 > price_low:
            passive_check_orders = buy_order_graph[i+1][1]
    if passive_check_orders > volume * 2:
        return False, None
    # Вычисляем "эффективное" количество ордеров для каждого уровня:
    # Для каждого уровня effective_qty = aggregated_qty текущего уровня - aggregated_qty следующего уровня
    effective_orders = []
    for i, order in enumerate(buy_order_graph):
        price_level = order[0]
        aggregated_qty = order[1]
        next_aggregated_qty = buy_order_graph[i + 1][1] if i < len(buy_order_graph) - 1 else 0
        effective_qty = aggregated_qty - next_aggregated_qty
        effective_orders.append((price_level, effective_qty))

    # Фильтруем ордера, у которых цена находится между threshold_74 и threshold_82
    filtered_orders = [(p, q) for p, q in effective_orders if threshold_74 < p <= threshold_82]
    # Сортируем по возрастанию цены для последовательного прохода от нижнего порога
    filtered_orders.sort(key=lambda x: x[0])

    candidate_price = round(threshold_74, 2)
    print(f"Начинаем с candidate_price = {candidate_price:.2f}")

    for price_level, effective_qty in filtered_orders:
        if price_level <= candidate_price:
            continue

        # Вычисляем динамический множитель и пороговое значение
        multiplier = 1 + (max_multiplier - 1) * ((price_level - threshold_74) / (threshold_82 - threshold_74))
        dynamic_threshold = base_wall_qty_threshold * multiplier

        if effective_qty >= dynamic_threshold:
            candidate_price = price_level + 0.01
            print(f"Оrдер на {price_level:.2f} с эффективным количеством {effective_qty:.2f} (порог {dynamic_threshold:.2f}) "
                  f"считается стенкой. Новая candidate_price = {candidate_price:.2f}")

    if candidate_price >= threshold_82:
        return False, None

    return True, candidate_price


if __name__ == "__main__":
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    
    service = Service()
    driver = webdriver.Chrome(service=service, options=options)

    # Регистрируем обработчик сигнала (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)
    steam_login(driver)

    with open("/home/pustrace/programming/steam_parser/main/database/logs.json", "r") as file:
        logs = json.load(file)
    with open("/home/pustrace/programming/steam_parser/main/database/perfect.json", "r") as file:
        perfect = json.load(file)
    with open ("/home/pustrace/programming/trade/steam/database/item_nameids.json", "r", encoding="utf-8") as f:
        item_nameids = json.load(f)
    with open ("/home/pustrace/programming/trade/steam/database/orders.json", "r") as file:
        orders = json.load(file)
    

    consecutive_errors = 0
    max_attempts = 6
    passive_check_orders = 0


    for skin, data in sorted(perfect.items(), key=lambda x: x[1].get("weight_of_items", 0), reverse=True):
        # start of passive analyze
        approx_min = data.get("approx_min")
        approx_max = data.get("approx_max")
        median_price = data.get("median_price")
        lowest_price = data.get("lowest_price")
        volume = data.get("volume")
        weight_number_of_items = data.get("weight_number_of_items")
        approx_price = None
        if approx_min is None or approx_max is None:
            print(f"Не удалось получить данные о цене для '{skin}'")
        
        if median_price is not None:
            current_price_pass = median_price
        else:
            current_price_pass = lowest_price
        
        if (approx_max - approx_min) > current_price_pass*0.13:
            approx_price = approx_min
        
        skin_orders = orders.get(skin, {})
        buy_order_graph = skin_orders.get("buy_order_graph", [])
        for i in range(len(buy_order_graph) - 1):
            price_high = buy_order_graph[i][0]
            price_low = buy_order_graph[i+1][0]
            if price_high > current_price_pass > price_low:
                passive_check_orders = buy_order_graph[i+1][1]
        if passive_check_orders > volume * 3:
            # End of passive analyze
            if skin in item_nameids:
                skin_id = item_nameids[skin]
            if skin in logs:
                print(f"Логи для '{skin}' уже существуют")
                continue
            
            if skin in orders:
                date_orders = orders[skin].get("timestamp_orders")
                timestamp_orders = datetime.fromisoformat(date_orders).date()
            if skin in perfect:
                date_price = perfect[skin].get("timestamp")    
                timestamp_price = datetime.fromisoformat(date_price).date()
            
            # Active analyze
            price, orders = get_market_data(skin, skin_id, timestamp_orders, timestamp_price)
            
            decision, order_price = analyze_orders_weights(price, orders)
            
            # Buy logic
            if decision:
                url = generate_market_url(skin)
                buy_skin(driver, url, order_price, weight_number_of_items)
                logs[skin] = {"order_price": order_price,
                              "weight_number_of_items": weight_number_of_items,
                              "url": url,
                              "timestamp": datetime.now().isoformat()}
                save_data(logs, "/home/pustrace/programming/trade/steam/database/logs.json")
        
        
    print("Выставление ордеров завершенно.")
