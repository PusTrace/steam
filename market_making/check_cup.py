from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
import time
import json
import re
import sys
import signal
import os
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException
from datetime import datetime

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
from utils.utils import save_data, signal_handler, generate_market_url

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
                time.sleep(30)
                consecutive_errors += 1
                driver.refresh()
                if consecutive_errors >= max_attempts:
                    driver.quit()
        
        time.sleep(1)
        try:
            link_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#sih_market_commodity_order_spread > div.footer_container > div.row.footer__left-side > div.row.button_container > a > div.text.fs-10")))
            driver.execute_script("arguments[0].click();", link_button)
            print("Клик по показать больще ордеров выполнен")
        except Exception as e:
            print("Ошибка при клике на показать больше ордеров:", e)
        
        elements = driver.find_elements(By.XPATH, "/html/body/div[1]/div[7]/div[4]/div[1]/div[4]/div[1]/div[2]/div/div[6]/div/div/div[2]/div[2]/span/span")
        if not elements:
            print("ордер не найден")
            return None, None, None

        my_order_price_str = elements[0].text
        cleaned_str = my_order_price_str.replace("₸", "").replace(" ", "").replace(",", ".")
        my_order_price = float(cleaned_str)

        sells_now_element = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "#sih_block_best_offer_of_marketplace_tabs_2 > div > div.row.stats_container > div > div.row.stats > div:nth-child(2) > span.stat_number.stat_week")
        ))
        sells_now_str = sells_now_element.text
        # Приводим цену к числовому значению (убираем пробел и символ валюты)
        sells_now = int(sells_now_str.replace(" ", ""))
        
        time.sleep(4)
        
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
        return parsed_data, my_order_price, sells_now
    finally:
        if not keep_browser_open:
            driver.quit()  # Закрытие всех вкладок и завершение работы браузера

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

def analyze_for_cancel_v1(orders, my_price, current_sells):
    """
    Анализирует список ордеров и определяет, нужно ли убирать ордер.
    """
    return sum(order["quantity"] for order in orders if order["price"] < my_price) > (current_sells * 1.5)


if __name__ == "__main__":
    options = webdriver.ChromeOptions()
    options.add_extension("/home/pustrace/programming/trade/steam/extensions/steam_invenory_helper2.3.1_0.crx")
    options.add_argument("--start-maximized")
    
    service = Service()
    driver = webdriver.Chrome(service=service, options=options)

    # Регистрируем обработчик сигнала (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)
    steam_login(driver)

    with open("/home/pustrace/programming/trade/steam/database/timer.json", "r") as file:
        skins = json.load(file)
    
    consecutive_errors = 0
    max_attempts = 6
        

    for skin in skins:
            # Если для скина уже существует отметка о продаже или отмене ордера, пропускаем его
        if skin in skins and ("timestamp_when_canceled" in skins[skin]
                                    or "timestamp_place_to_sell" in skins[skin]
                                    or "not_found" in skins[skin]
                                    ):
            print(f"Пропускаем {skin}: уже обработан.")
            continue

        url = generate_market_url(skin)

        print(f"\nПолучение данных для '{skin}'...")
        orders, my_order_price, sells_now = get_orders_data(url, keep_browser_open=True)
        
        if my_order_price is None:
            skins[skin] = {"not_found": datetime.now().isoformat()}
            save_data(skins, "/home/pustrace/programming/trade/steam/database/timer.json")
            continue
        
        decision = analyze_for_cancel_v1(orders, my_order_price, sells_now)
        if decision:
            cancel_order()
            skins[skin] = {"canceled_order_price": my_order_price, "timestamp_when_canceled": datetime.now().isoformat()}
            save_data(skins, "/home/pustrace/programming/trade/steam/database/timer.json")
            
        else:
            skins[skin] = {"timestamp_when_checked": datetime.now().isoformat()}
            save_data(skins, "/home/pustrace/programming/trade/steam/database/timer.json")
        
        
    print("Парсинг завершён.")
