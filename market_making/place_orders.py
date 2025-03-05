from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import Select
import time
import json
import re
import subprocess
import sys
import signal
import urllib.parse
import base64
import os
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from datetime import datetime

def generate_market_url(skin_name):
    """Генерирует URL для скина на маркете Steam."""
    encoded_name = urllib.parse.quote(skin_name)
    url = f"https://steamcommunity.com/market/listings/730/{encoded_name}"
    return url

def load_existing_database(filename):
    """Загружает (или создаёт) базу данных, в которую будем добавлять новые записи."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"Ошибка при загрузке базы данных из {filename}: {e}")
        return {}
    
def check_skin_in_database(skin, market_data):
    """Проверяет, есть ли данные о скине в базе данных."""
    if skin in market_data:
        print(f"'{skin}' уже существует в базе")
        return True
    return False

def save_data(new_data, filename="/home/pustrace/programming/steam_parser/main/database/timer.json"):
    """Сохраняет или обновляет данные в JSON файле."""
    try:
        existing_data = load_existing_database(filename)
        existing_data.update(new_data)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=4)
        print(f"Данные успешно сохранены в {filename}")
    except Exception as e:
        print(f"Ошибка при сохранении данных: {e}")

def load_skins_from_json(filename):
    """Загружает список скинов из JSON файла."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            skins = json.load(f)
        return skins
    except Exception as e:
        print(f"Ошибка при чтении файла {filename}: {e}")
        return []

def signal_handler(signum, frame):
    """Обработчик сигнала прерывания."""
    global market_data
    print("\nПолучен сигнал прерывания. Сохраняем данные перед выходом...")
    if 'market_data' in globals() and market_data:
        save_data(market_data)
    print("Данные сохранены. Завершение работы.")
    sys.exit(0)

def run_router_script():
    """Запускает router.py."""
    try:
        subprocess.run(["python", "/home/pustrace/programming/steam_parser/utils/router.py"], check=True)
        print("router.py успешно запущен.")
        print("Ожидаем 5 минут...")
        time.sleep(300)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при запуске router.py: {e}")

def get_orders_data(url, keep_browser_open=False):
    """
    Открывает страницу, кликает по нужным элементам и извлекает информацию.
    Возвращает список строк с информацией.
    """

    wait = WebDriverWait(driver, 10)  # Ожидание до 10 секунд
    
    try:
        driver.get(url)
        consecutive_errors = 0

        while consecutive_errors < max_attempts:
            try:
                span_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#market_buyorder_info_show_details > span")))
                driver.execute_script("arguments[0].click();", span_button)
                print("Клик по подробнее выполнен")
                wait.until(EC.invisibility_of_element(span_button))
                print("Кнопка подробнее исчезла, можно переходить к следующему шагу.")
                break
            except Exception as e:
                print("Ошибка при клике на span:", e)
                time.sleep(300)
                consecutive_errors += 1
                driver.refresh()
                if consecutive_errors >= max_attempts:
                    driver.quit()
                    # print("Превышено количество ошибок подряд. Запускаем router.py...")
                    # run_router_script()
                    # print(consecutive_errors)
                    # consecutive_errors = 0
                    # driver.refresh()
        
        time.sleep(1)
        try:
            link_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#sih_market_commodity_order_spread > div.footer_container > div.row.footer__left-side > div.row.button_container > a > div.text.fs-10")))
            driver.execute_script("arguments[0].click();", link_button)
            print("Клик по показать больще ордеров выполнен")
        except Exception as e:
            print("Ошибка при клике на показать больше ордеров:", e)
        
        
        # Извлекаем стенку с ордерами
        time.sleep(4)
        price_now_element = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "#sih_block_best_offer_of_marketplace_tabs_2 > div > div.row.markets_container > div.column.steam_container > div.price")
        ))
        price_now_str = price_now_element.text
        # Приводим цену к числовому значению (убираем пробел и символ валюты)
        price_now = float(price_now_str.replace(" ₸", "").replace(" ", ""))
        
        sells_now_element = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "#sih_block_best_offer_of_marketplace_tabs_2 > div > div.row.stats_container > div > div.row.stats > div:nth-child(2) > span.stat_number.stat_week")
        ))
        sells_now_str = sells_now_element.text
        # Приводим цену к числовому значению (убираем пробел и символ валюты)
        sells_now = int(sells_now_str.replace(" ", ""))
        
        data_element = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "#market_commodity_buyreqeusts_table")))
        lines = data_element.text.split("\n")
        start_index = next((i for i, line in enumerate(lines) if "Price Margin Quantity" in line), -1) + 1
        lines = lines[start_index:]
        
        pattern = re.compile(r"([\d.,]+) ₸ ([+-][\d.,]+) ₸ \(([\d-]+)%\)\s+(\d+)")
        parsed_data = []
        
        for line in lines:
            match = pattern.search(line)
            if match:
                price, margin, percentage, quantity = match.groups()
                parsed_data.append({
                    "price": float(price.replace(",", ".")),
                    "margin": float(margin.replace(",", ".")),
                    "percentage": int(percentage),
                    "quantity": int(quantity)
                })

        if not keep_browser_open:
            driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return parsed_data, price_now, sells_now
    finally:
        if not keep_browser_open:
            driver.quit()  # Закрытие всех вкладок и завершение работы браузера

def analyze_orders_v6(orders, current_price, current_sells, max_multiplier=2.0):
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

def steam_login(driver):
    login_url = "https://steamcommunity.com/login/home/"
    driver.get(login_url)
    
    WebDriverWait(driver, 99999999999).until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[7]/div[7]/div[1]/div[1]/div/div/div/div[1]/div[1]/span[1]")))
    print("Авторизация в Steam выполнена.")
    
def buy_skin(order_price):
    wait = WebDriverWait(driver, 10)  # Ожидание до 10 секунд
    
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


if __name__ == "__main__":
    options = webdriver.ChromeOptions()
    options.add_extension("/home/pustrace/programming/steam_parser/main/extensions/steam_invenory_helper2.3.1_0.crx")
    options.add_argument("--start-maximized")
    
    service = Service()
    driver = webdriver.Chrome(service=service, options=options)

    # Регистрируем обработчик сигнала (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)
    steam_login(driver)

    
    skins = load_skins_from_json("/home/pustrace/programming/steam_parser/main/database/perfect.json")
    market_data = load_existing_database("/home/pustrace/programming/steam_parser/main/database/timer.json")
    
    consecutive_errors = 0
    max_attempts = 6
        

    for skin in skins:
        if check_skin_in_database(skin, market_data):
            print(f"Ордера для '{skin}' уже существуют")
            continue

        url = generate_market_url(skin)

        print(f"\nПолучение данных для '{skin}'...")
        orders, current_price, current_sells = get_orders_data(url, keep_browser_open=True)
        
        # анализ информации покупать или нет и за сколько
        decision, order_price = analyze_orders_v6(orders, current_price, current_sells)
        if decision:
            buy_skin(order_price)
            market_data[skin] = {"order_price": order_price, "timestamp": datetime.now().isoformat()}
            save_data(market_data)
            
        else:
            print("\nНе покупать – условие перебития не выполнено (слишком много ордеров или цена достигла 82%).")
        
        
    print("Парсинг завершён.")
