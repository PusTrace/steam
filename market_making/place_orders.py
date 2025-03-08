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
from datetime import datetime

import sys
import os
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
from utils.utils import save_data, signal_handler
from orders.get_order_info import get_orders
from price.get_steam_price import get_steam_price

def get_market_data(skin, skin_id, timestamp_orders, timestamp_price):
    today = datetime.date.today().isoformat()  # Пример формата 'YYYY-MM-DD'
    
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
    
def buy_skin(order_price, url):
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

def analyze_orders_weights(orders, current_price, current_sells, max_multiplier=2.0):
    threshold_75 = current_price * 0.69
    threshold_82 = current_price * 0.77
    base_wall_qty_threshold = current_sells * 0.1

    orders_above_82 = [o for o in orders if o["price"] > threshold_82]
    cumulative_qty = sum(o["quantity"] for o in orders_above_82)
    if cumulative_qty > current_sells * 1.2:
        return False, None

    candidate_price = round(threshold_75, 2)
    print(f"Начинаем с candidate_price = {candidate_price:.2f}")

    relevant_orders = [o for o in orders if threshold_75 < o["price"] <= threshold_82]
    relevant_orders.sort(key=lambda o: o["price"])

    for order in relevant_orders:
        if order["price"] <= candidate_price:
            continue

        multiplier = 1 + (max_multiplier - 1) * ((order["price"] - threshold_75) / (threshold_82 - threshold_75))
        dynamic_threshold = base_wall_qty_threshold * multiplier

        if order["quantity"] >= dynamic_threshold:
            candidate_price = order["price"] + 0.01
            print(f"Оrдер на {order['price']:.2f} с количеством {order['quantity']:.2f} (порог {dynamic_threshold:.2f}) " 
                  f"считается стенкой. Новая candidate_price = {candidate_price:.2f}")

    if candidate_price >= threshold_82:
        return False, None

    return True, candidate_price

if __name__ == "__main__":
    options = webdriver.ChromeOptions()
    options.add_extension("/home/pustrace/programming/steam_parser/main/extensions/steam_invenory_helper2.3.1_0.crx")
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
    today = date.today()  # Текущая дата

    for skin, data in perfect.items():
        # Перед активным анализом добавить пассивный анализ
            
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
        
        # Активный анализ
        price, orders = get_market_data(skin, skin_id, timestamp_orders, timestamp_price)
        
        decision, order_price, num_of_skins = analyze_orders_weights(price, orders)
        if decision:
            buy_skin(order_price, skin)
            logs[skin] = {"order_price": order_price, "timestamp": datetime.now().isoformat()}
            save_data(logs)
        
        
    print("Выставление ордеров завершенно.")
