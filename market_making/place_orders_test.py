from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import sys
import os

# Импортируем selenium-stealth для обхода антибот-защиты
from selenium_stealth import stealth

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
from utils.utils import generate_market_url

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

def steam_login(driver):
    login_url = "https://steamcommunity.com/login/home/"
    driver.get(login_url)
    
    # Ожидаем появления элемента, свидетельствующего об успешном входе (например, имя пользователя)
    WebDriverWait(driver, 99999999999).until(
        EC.presence_of_element_located((By.CLASS_NAME, "actual_persona_name"))
    )
    print("Авторизация в Steam выполнена.")

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
        time.sleep(5)
        btn_to_complite.click()
        time.sleep(2)
    except TimeoutException:
        print("Timeout: Элементы не найдены")
        return
    except Exception as e:
        print("Ошибка:", e)
        driver.quit()

def load_cookies(driver, cookies):
    """Загружает cookies в драйвер."""
    driver.get("https://steamcommunity.com/")
    for cookie in cookies:
        # Удаляем поле 'expiry', если оно присутствует, чтобы не возникло ошибок
        if 'expiry' in cookie:
            cookie.pop('expiry')
        driver.add_cookie(cookie)
    driver.refresh()

if __name__ == "__main__":
    skin = "SSG 08 | Abyss (Well-Worn)"
    order_price = "80"
    weight_number_of_items = 2  # Для Steam обычно требуется целое число

    # 1. Запуск драйвера в обычном режиме для логина
    driver_normal = setup_driver(headless=False)
    steam_login(driver_normal)
    
    # Сохраняем cookies после успешного входа
    cookies = driver_normal.get_cookies()
    driver_normal.quit()  # Закрываем обычный браузер

    # 2. Запуск драйвера в headless-режиме
    driver_headless = setup_driver(headless=True)
    load_cookies(driver_headless, cookies)
    
    # Выставление ордера в headless-режиме
    url = generate_market_url(skin)
    buy_skin(driver_headless, url, order_price, weight_number_of_items)
    
    print("Выставление ордеров завершено.")
    driver_headless.quit()
