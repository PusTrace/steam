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
from utils.utils import save_data

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
        save_data(market_data, "steam/database/timer.json")
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
        try:
            check_for_errors = wait.until(EC.presence_of_element_located(
                (By.XPATH, "/html/body/div[1]/div[7]/div[4]/div[1]/div[4]/div[1]/div[2]/div/div")
            ))
            if check_for_errors.text.strip() == "There are no listings for this item.":
                return None
        except TimeoutException:
            # Если элемент не найден, продолжаем выполнение
            pass

        # Извлекаем стенку с ордерами
        time.sleep(4)
        price_now_element = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "#sih_block_best_offer_of_marketplace_tabs_2 > div > div.row.markets_container > div.column.steam_container > div.price")
        ))
        price_now_str = price_now_element.text
        # Приводим цену к числовому значению (убираем пробел и символ валюты)
        price_now = float(price_now_str.replace(" ₸", "").replace(" ", ""))
        

        if not keep_browser_open:
            driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return price_now
    finally:
        if not keep_browser_open:
            driver.quit()  # Закрытие всех вкладок и завершение работы браузера

def analyze_to_sell_v1(current_price, order_price):
    if order_price is None:
        return True, current_price
    minimum_price = order_price*1.15
    if current_price < minimum_price:
        return True, minimum_price
    else:
        return True, current_price

def steam_login(driver):
    login_url = "https://steamcommunity.com/login/home/"
    driver.get(login_url)
    
    WebDriverWait(driver, 99999999999).until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[7]/div[7]/div[1]/div[1]/div/div/div/div[1]/div[1]/span[1]")))
    print("Авторизация в Steam выполнена.")


if __name__ == "__main__":
    options = webdriver.ChromeOptions()
    options.add_extension("/home/pustrace/programming/trade/steam/extensions/steam_invenory_helper2.3.1_0.crx")
    options.add_argument("--start-maximized")
    
    service = Service()
    driver = webdriver.Chrome(service=service, options=options)

    # Регистрируем обработчик сигнала (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)
    steam_login(driver)

    
    skins = load_skins_from_json("/home/pustrace/programming/trade/steam/database/timer.json")
    market_data = load_existing_database("/home/pustrace/programming/steam_parser/main/database/timer.json")
    
    consecutive_errors = 0
    max_attempts = 6
        
for skin_name, skin_data in skins.items():
    if skin_name in market_data and "sell_price" in market_data[skin_name] and "timestamp_place_to_sell" in market_data[skin_name] and "This_item_is_missing" in market_data[skin_name]:
        print(f"'{skin_data}' уже обработан")
        continue
    if "cache_expiration" not in skin_data:
        continue
    elif skin_data["cache_expiration"] is None:
        url = generate_market_url(skin_name)
        current_price = get_orders_data(url, keep_browser_open=True)
        if current_price is None:
            market_data[skin_name] = {"This_item_is_missing": datetime.now().isoformat()}
            save_data(market_data, "steam/database/timer.json")
            continue
        order_price = skin_data.get("order_price")
        decision, sell_price = analyze_to_sell_v1(current_price, order_price)
        if decision:
            print(f"Продать '{skin_name}' на {sell_price}")
            # автопродажа не реализовано
            # sell_skin(sell_price)
            market_data[skin_name] = {"sell_price": sell_price, "timestamp_place_to_sell": datetime.now().isoformat()}
            save_data(market_data, "steam/database/timer.json")
    else:
        continue
        
        # # анализ информации покупать или нет и за сколько

        
        
    print("Парсинг завершён.")
