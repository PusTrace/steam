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

import sys
import os
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
from market_making.place_orders import setup_driver
from utils.utils import save_data, generate_market_url
from price.get_steam_price import get_steam_price


def analyze_if_smaller(current_price, my_order_price):
    if current_price*0.86 < my_order_price:
        return True
    else:
        return False
    

def steam_login(driver):
    login_url = "https://steamcommunity.com/login/home/"
    driver.get(login_url)
    
    # Ожидаем появления элемента, свидетельствующего об успешном входе (например, имя пользователя)
    WebDriverWait(driver, 99999999999).until(
        EC.presence_of_element_located((By.CLASS_NAME, "actual_persona_name"))
    )
    print("Авторизация в Steam выполнена.")
    
def cancel_order(url):
    wait = WebDriverWait(driver, 10)  # Ожидание до 10 секунд
    driver.get(url)
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
    driver = setup_driver(headless=False)
    steam_login(driver)

    with open("/home/pustrace/programming/trade/steam/database/logs.json", "r", encoding="utf-8") as f:
        logs = json.load(f)
        

    for skin, data in logs.items():
        print(f"Обрабатываем: {skin}")
        my_order_price = data.get("order_price")
        print(f"Отправляем запрос: {skin}")
        data_price = get_steam_price(skin)
        lowest_price_str = data_price.get("lowest_price")
        median_price_str = data_price.get("median_price")
        
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
        
        current_price = median_price if median_price is not None else lowest_price
        
        decision = analyze_if_smaller(current_price, my_order_price)
        if decision:
            print(f"Наше предложение меньше текущей цены на {skin}. Отменяем ордер.")
            url = generate_market_url(skin)
            cancel_order(url)
            data[skin] = {"timestamp_when_smaller": datetime.now().isoformat()}
            save_data(data, "/home/pustrace/programming/trade/steam/database/timer.json")
        
        
    print("Парсинг завершён.")
