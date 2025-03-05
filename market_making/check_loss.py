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

def save_data(new_data, filename):
    """Сохраняет или обновляет данные в JSON файле."""
    try:
        existing_data = load_existing_database(filename)
        for key, value in new_data.items():
            if key in existing_data:
                if isinstance(existing_data[key], list):
                    existing_data[key].append(value)
                elif isinstance(existing_data[key], dict):
                    existing_data[key].update(value)
                else:
                    existing_data[key] = [existing_data[key], value]
            else:
                existing_data[key] = value
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


def get_orders_data(url, keep_browser_open=False):
    """
    Открывает страницу, кликает по нужным элементам и извлекает информацию.
    Возвращает список строк с информацией.
    """

    wait = WebDriverWait(driver, 10)  # Ожидание до 10 секунд
    
    try:
        driver.get(url)
        time.sleep(2)
        consecutive_errors = 0

        while consecutive_errors < max_attempts:
            try:
                price_now_element = wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#sih_block_best_offer_of_marketplace_tabs_2 > div > div.row.markets_container > div.column.steam_container > div.price")
                ))
                price_now_str = price_now_element.text
                # Приводим цену к числовому значению (убираем пробел и символ валюты)
                price_now = float(price_now_str.replace(" ₸", "").replace(" ", ""))
                break
            except Exception as e:
                print("Ошибка:", e)
                time.sleep(30)
                consecutive_errors += 1
                driver.refresh()
                if consecutive_errors >= max_attempts:
                    driver.quit()
                    
        elements = driver.find_elements(By.XPATH, "/html/body/div[1]/div[7]/div[4]/div[1]/div[4]/div[1]/div[2]/div/div[6]/div/div/div[2]/div[2]/span/span")
        if not elements:
            print("ордер не найден")
            return None, None

        my_order_price_str = elements[0].text
        cleaned_str = my_order_price_str.replace("₸", "").replace(" ", "").replace(",", ".")
        my_order_price = float(cleaned_str)


        if not keep_browser_open:
            driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return price_now, my_order_price
    finally:
        if not keep_browser_open:
            driver.quit()  # Закрытие всех вкладок и завершение работы браузера

def analyze_if_smaller(current_price, my_order_price):
    if current_price*0.86 < my_order_price:
        return True
    else:
        return False
    

def steam_login(driver):
    login_url = "https://steamcommunity.com/login/home/"
    driver.get(login_url)
    
    WebDriverWait(driver, 99999999999).until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[7]/div[7]/div[1]/div[1]/div/div/div/div[1]/div[1]/span[1]")))
    print("Авторизация в Steam выполнена.")
    
def cancel_order():
    wait = WebDriverWait(driver, 10)  # Ожидание до 10 секунд

    try:
        btn_cancel = wait.until(EC.presence_of_element_located(
                (By.XPATH, "/html/body/div[1]/div[7]/div[4]/div[1]/div[4]/div[1]/div[2]/div/div[6]/div/div/div[2]/div[5]/div/a/span[2]")
            ))
        driver.execute_script("arguments[0].scrollIntoView();", btn_cancel)
        ActionChains(driver).move_to_element(btn_cancel).perform()
        btn_cancel.click()
        time.sleep(2)  # Пауза для успешной отмены ордера
        print("Ордер отменен.")

    except TimeoutException:
        return
    except Exception as e:
        driver.quit()


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
    market_data = load_existing_database("/home/pustrace/programming/trade/steam/database/timer.json")
    
    consecutive_errors = 0
    max_attempts = 6
        

    for skin in skins:
            # Если для скина уже существует отметка о продаже или отмене ордера, пропускаем его
        if skin in market_data and ("timestamp_when_canceled" in market_data[skin] or "timestamp_place_to_sell" in market_data[skin] or "not_found" in market_data[skin] or "timestamp_when_smaller" in market_data[skin]):
            print(f"Пропускаем {skin}: уже обработан.")
            continue


        url = generate_market_url(skin)

        print(f"\nПолучение данных для '{skin}'...")
        current_price, my_order_price = get_orders_data(url, keep_browser_open=True)
        
        if my_order_price is None:
            market_data[skin] = {"not_found": datetime.now().isoformat()}
            save_data(market_data, "/home/pustrace/programming/trade/steam/database/timer.json")
            continue
        
        # анализ информации покупать или нет и за сколько
        decision = analyze_if_smaller(current_price, my_order_price)
        if decision:
            cancel_order()
            market_data[skin] = {"timestamp_when_smaller": datetime.now().isoformat()}
            save_data(market_data, "/home/pustrace/programming/trade/steam/database/timer.json")
        else:
            market_data[skin] = {"timestamp_when_smaller_checked": datetime.now().isoformat()}
            save_data(market_data, "/home/pustrace/programming/trade/steam/database/timer.json")
            print(skin)
        
        
    print("Парсинг завершён.")
