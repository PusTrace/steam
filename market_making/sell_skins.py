#get_inventory
import requests
import json
import os
import sys
import signal
from datetime import datetime, time
from selenium_stealth import stealth
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
from utils.utils import save_data, signal_handler
from market_making.place_orders import get_market_data

        
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

def get_inventory(steam_cookie=None):
    url = 'https://steamcommunity.com/profiles/76561198857946351/inventory/json/730/2/?l=english'
    session = requests.Session()
    
    # Если кука не была передана, падаем обратно на os.getenv (на всякий случай)
    if steam_cookie is None:
        steam_cookie = os.getenv("STEAM_LOGIN_SECURE")
        if steam_cookie is None:
            print("Ошибка: не найдена кука steamLoginSecure ни в параметрах, ни в переменных окружения!")
            return
    cookies = {'steamLoginSecure': steam_cookie}
    session.cookies.update(cookies)
    
    headers = {
        'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/58.0.3029.110 Safari/537.36')
    }
    response = session.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        with open('/home/pustrace/programming/trade/steam/database/inventory.json', 'r') as file:
            skins_data = json.load(file)
        # Обработка полученных предметов
        for item in data.get('rgDescriptions', {}).values():
            market_hash_name = item.get('market_hash_name')
            cache_expiration = item.get('cache_expiration', None)
            skins_data[market_hash_name] = {'cache_expiration': cache_expiration}
            save_data(skins_data, '/home/pustrace/programming/trade/steam/database/inventory.json')
        return skins_data
    else:
        print(f"Ошибка запроса инвентаря: статус {response.status_code}")

def check_cup(current_price, my_my_price, orders):

    return True

def check_loss(current_price, my_price):
    if current_price*0.86 < my_price:
        return True
    else:
        return False
    
def sell_skin():
    print("sell_skin")
    
def cancel_order(skin, url):
    print("cancel_order")

#main code
if __name__ == "__main__":
    margin = 0
    # setting tornet
    TOR_SOCKS_PROXY = "socks5h://127.0.0.1:9050"
    proxies={"http": TOR_SOCKS_PROXY, "https": TOR_SOCKS_PROXY}


    # Регистрируем обработчик сигнала (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)
    
    # 1. Запуск драйвера в обычном режиме для логина
    driver_normal = setup_driver(headless=False)
    steam_login(driver_normal)
    cookies = driver_normal.get_cookies()
    steam_cookie = None
    for cookie in cookies:
        if cookie.get("name") == "steamLoginSecure":
            steam_cookie = cookie.get("value")
            break

    if steam_cookie is None:
        print("Не найдена кука steamLoginSecure!")
    driver_normal.quit()

    # Передаём полученную куку в get_inventory:
    inventory = get_inventory(steam_cookie)


    driver_headless = setup_driver(headless=True)
    load_cookies(driver_headless, cookies)

    with open("/home/pustrace/programming/trade/steam/database/logs.json", "r") as file:
        logs = json.load(file)
    with open ("/home/pustrace/programming/trade/steam/database/item_nameids.json", "r", encoding="utf-8") as f:
        item_nameids = json.load(f)
    with open ("/home/pustrace/programming/trade/steam/database/orders.json", "r") as file:
        all_orders = json.load(file)
    with open ("/home/pustrace/programming/trade/steam/database/database.json", "r") as file:
        database = json.load(file)
    
    # # Сначала обрабатываем те, которых нет в инвентаре
    # for skin, data in logs.items():
    #     if skin in inventory:
    #         continue  # пропускаем, обработаем позже

    #     my_price = data.get("order_price")
    #     weight_number_of_items = data.get("weight_number_of_items")
    #     url = data.get("url")
    #     timestamp_logs = data.get("timestamp")
    #     timestamp = datetime.fromisoformat(timestamp_logs).date()
        
    #     if skin in item_nameids:
    #         skin_id = item_nameids[skin]
        
    #     if skin in all_orders:
    #         date_orders = all_orders[skin].get("timestamp_orders")
    #         timestamp_orders = datetime.fromisoformat(date_orders).date()
        
    #     if skin in database:
    #         date_price = database[skin].get("timestamp")    
    #         timestamp_price = datetime.fromisoformat(date_price).date()

    #     print(f"Получение данных для '{skin}' .")
    #     price, orders = get_market_data(skin, skin_id, timestamp_orders, timestamp_price, proxies)
    #     cup = check_cup(price, my_price, orders)
    #     loss = check_loss(price, my_price)
    #     if cup or loss:
    #         cancel_order(skin, url)
            

    # Теперь обрабатываем предметы, которые есть в инвентаре
    for skin, data in logs.items():
        if skin not in inventory:
            continue  # уже обработано выше

        my_price = data.get("order_price")
        url = data.get("url")
        if skin in item_nameids:
            skin_id = item_nameids[skin]
        
        if skin in all_orders:
            date_orders = all_orders[skin].get("timestamp_orders")
            timestamp_orders = datetime.fromisoformat(date_orders).date()
        
        if skin in database:
            date_price = database[skin].get("timestamp")    
            timestamp_price = datetime.fromisoformat(date_price).date()

        print(f"Получение данных для '{skin}' .")
        price, orders = get_market_data(skin, skin_id, timestamp_orders, timestamp_price, proxies)

        lowest_price = price.get("lowest_price")
        median_price = price.get("median_price")
        
        
        if median_price:
            current_price = median_price
        else:
            current_price = lowest_price
        
        margin = my_price - current_price
        
        if 0 > margin > -15:
            sell_skin(driver_headless, url, my_price)
            logs[skin] = {
                "my_price": my_price,
                "margin": margin,
                "timestamp_when_placed_to_sell": datetime.now().isoformat()
            }
        elif margin > 0:
            sell_skin(driver_headless, url, my_price)
            logs[skin] = {
                "my_price": my_price,
                "margin": margin,
                "timestamp": datetime.now().isoformat()
            }
        else:
            logs[skin] = {
                "my_price": my_price,
                "margin": margin,
                "timestamp": datetime.now().isoformat()
            }

        save_data(logs, "/home/pustrace/programming/trade/steam/database/logs.json")

    
    print("Выставление ордеров завершено.")
    driver_headless.quit()