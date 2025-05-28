#get_inventory
import requests
from bs4 import BeautifulSoup
import json
import os
import sys
import signal
import pandas as pd
from datetime import datetime, time
from selenium_stealth import stealth
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from place_orders import get_market_data

        
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


def get_inventory(cookies_from_browser):
    url = 'https://steamcommunity.com/inventory/76561198857946351/730/2'
    session = requests.Session()
    
    for cookie in cookies_from_browser:
        session.cookies.set(cookie['name'], cookie['value'])
    
    headers = {
        'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/58.0.3029.110 Safari/537.36')
    }
    
    response = session.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        skins_data = {}

        # Получаем списки assets и описаний
        assets = data.get('assets', [])
        descriptions = data.get('descriptions', [])

        # Собираем все данные по asset'ам в список
        asset_data_list = []
        for asset in assets:
            asset_info = {
                "assetid": asset.get('assetid'),
                "classid": asset.get('classid'),
                "instanceid": asset.get('instanceid')
            }
            asset_data_list.append(asset_info)

        # Проходим по описаниям и ищем в asset_data_list совпадения по classid и instanceid
        for item in descriptions:
            market_hash_name = item.get('market_hash_name')
            marketable = item.get('marketable')
            classid = item.get('classid')
            instanceid = item.get('instanceid')
            asset_ids = []

            for asset_item in asset_data_list:
                if classid == asset_item.get('classid') and instanceid == asset_item.get('instanceid'):
                    asset_ids.append(asset_item.get('assetid'))
            
            # Записываем собранные данные в skins_data
            skins_data[market_hash_name] = {
                'marketable': marketable,
                'classid': classid,
                'instanceid': instanceid,
                'asset_ids': asset_ids
            }
        return skins_data
    else:
        print(f"Ошибка запроса инвентаря: статус {response.status_code}")
        

def check_CupAndLoss(my_price, current_price, orders, volume):
    if round(current_price, 2) / 0.87 < round(my_price, 2):
        return True

    if volume is None:
        print("Объем равен None")
        return False
    else:
        volume = int(volume.replace(" ", "").replace(",", ""))
    buy_order_graph = orders.get("buy_order_graph")
    
    df = pd.DataFrame(buy_order_graph, columns=['price', 'count', 'description'])
    df['price_rounded'] = df['price'].round(2)

    # Округляем my_price отдельно
    my_price_rounded = round(my_price, 2)
    
    # Вместо query просто фильтруем по маске
    match = df[df['price_rounded'] == my_price_rounded]
    if not match.empty:
        order_count = int(match.iloc[0]['count'])
        return volume * 32 > order_count
    else:
        print(f"Ордер с ценой {my_price_rounded} не найден в списке. Ошибка в проверке CupAndLoss.")
        return False




def cancel_order(skin, buy_order_id, cookies):
    """Отменяет ордер на покупку скина."""
    url = "https://steamcommunity.com/market/cancelbuyorder/"  # исправил URL
    session = requests.Session()

    # Закидываем ВСЕ куки в сессию
    for cookie in cookies:
        session.cookies.set(cookie['name'], cookie['value'])

    # Вытаскиваем sessionid из куков
    sessionid = None
    for cookie in cookies:
        if cookie['name'] == 'sessionid':
            sessionid = cookie['value']
            break

    headers = {
        "Host": "steamcommunity.com",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:137.0) Gecko/20100101 Firefox/137.0",
        "Accept": "text/javascript, text/html, application/xml, text/xml, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "X-Prototype-Version": "1.7",
        "Origin": "https://steamcommunity.com",
        "Referer": "https://steamcommunity.com/market/",
        "Dnt": "1",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Te": "trailers",
        "Connection": "close"
    }

    data = {
        "sessionid": sessionid,
        "buy_orderid": buy_order_id
    }

    response = session.post(url, headers=headers, data=data)

    if response.status_code == 200:
        print(f"skin {skin} успешно убран из стенки. Ответ: {response.text}")
    else:
        print(f"Ошибка при попытке убрать skin {skin}: {response.status_code}\nОтвет: {response.text}")

    
def delete_order(skin):
    """Удаляет информацию о передаваемом skin из указанного JSON файла."""
    with open("/home/pustrace/programming/trade/steam/database/logs.json", "r") as file:
        data = json.load(file)
    if skin in data:
        del data[skin]
        with open("/home/pustrace/programming/trade/steam/database/logs.json", "w") as file:
            json.dump(data, file, indent=4)

def sell_skin(price, list_of_assets, cookies):
    url = "https://steamcommunity.com/market/sellitem/"
    price_for_steam = round(price * 100)

    session = requests.Session()

    # Закидываем ВСЕ куки в сессию
    for cookie in cookies:
        session.cookies.set(cookie['name'], cookie['value'])

    # Вытаскиваем sessionid из куков
    sessionid = None
    for cookie in cookies:
        if cookie['name'] == 'sessionid':
            sessionid = cookie['value']
            break

    headers = {
        "Host": "steamcommunity.com",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:137.0) Gecko/20100101 Firefox/137.0",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://steamcommunity.com",
        "Referer": "https://steamcommunity.com/profiles/76561198857946351/inventory",
        "Dnt": "1"
    }

    for asset in list_of_assets:
        data = {
            "sessionid": sessionid,
            "appid": "730",
            "contextid": "2",
            "assetid": asset,
            "amount": "1",
            "price": price_for_steam
        }
        response = session.post(url, headers=headers, data=data)

        if response.status_code == 200:
            print(f"Asset {asset} успешно выставлен на продажу.\nОтвет: {response.text}")
        else:
            print(f"Ошибка при продаже asset {asset}: {response.status_code}\nОтвет: {response.text}")


def get_list_of_my_orders(cookies_from_browser):
    url = "https://steamcommunity.com/market/"

    session = requests.Session()

    # Просто закидываем ВСЕ куки в сессию
    for cookie in cookies_from_browser:
        session.cookies.set(cookie['name'], cookie['value'])

    headers = {
        "Host": "steamcommunity.com",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:137.0) Gecko/20100101 Firefox/137.0",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://steamcommunity.com",
        "Referer": "https://steamcommunity.com/profiles/76561198857946351/inventory",
        "Dnt": "1"
    }

    response = session.get(url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        
        orders = soup.find_all("div", id=lambda x: x and x.startswith("mybuyorder_"))

        orders_dict = {}
        for order_div in orders:
            order_id_full = order_div.get("id")
            order_id = order_id_full.split("_")[1]

            item_name_tag = order_div.find("a", class_="market_listing_item_name_link")
            if item_name_tag:
                item_name = item_name_tag.text.strip()
                orders_dict[item_name] = order_id
            
        return orders_dict


#main code
if __name__ == "__main__":
    # setting tornet
    TOR_SOCKS_PROXY = "socks5h://127.0.0.1:9050"
    proxies={"http": TOR_SOCKS_PROXY, "https": TOR_SOCKS_PROXY}

    # Регистрируем обработчик сигнала (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)
    
    # 1. Запуск драйвера в обычном режиме для логина
    driver_normal = setup_driver(headless=False)
    steam_login(driver_normal)
    cookies = driver_normal.get_cookies()
    driver_normal.quit()

    # Передаём полученную куку в get_inventory:
    inventory = get_inventory(cookies)

    with open("/home/pustrace/programming/trade/steam/database/logs.json", "r") as file:
        logs = json.load(file)
    with open ("/home/pustrace/programming/trade/steam/database/item_nameids.json", "r", encoding="utf-8") as f:
        item_nameids = json.load(f)
    with open ("/home/pustrace/programming/trade/steam/database/orders.json", "r") as file:
        all_orders = json.load(file)
    with open ("/home/pustrace/programming/trade/steam/database/database.json", "r") as file:
        database = json.load(file)
    
    # # Сначала обрабатываем те, которых нет в инвентаре
    orders_dict = get_list_of_my_orders(cookies)
    for skin, data in logs.items():
        if skin in inventory:
            continue  # пропускаем, обработаем позже

        my_price = data.get("order_price")
        url = data.get("url")
        if skin in orders_dict:
            buy_order_id = orders_dict[skin]
        else:
            continue
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
        volume = price.get("volume")
        
        if median_price:
            current_price = float(median_price.replace("₸", "").replace(",", ".").replace(" ", "").strip())
        else:
            current_price = float(lowest_price.replace("₸", "").replace(",", ".").replace(" ", "").strip())
        
        CupAndLoss = check_CupAndLoss(my_price, current_price, orders, volume)
        if CupAndLoss:
            cancel_order(skin, buy_order_id, cookies)
            delete_order(skin)

    for skin, data in logs.items():
        if skin not in inventory:
            continue  # уже обработано выше
        list_of_assets = inventory[skin].get("asset_ids")

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
            current_price = float(median_price.replace("₸", "").replace(",", ".").replace(" ", "").strip())
        else:
            current_price = float(lowest_price.replace("₸", "").replace(",", ".").replace(" ", "").strip())
        
        for_margin = current_price - my_price/0.87
        
        margin = for_margin * 100 / my_price 
        
        if margin < 0:
            sell_skin(my_price, list_of_assets, cookies)
            logs[skin] = {
                "my_sell_price": round(my_price/0.87, 2),
                "margin-": margin,
                "timestamp_when_placed_to_sell": datetime.now().isoformat()
            }
        else:
            sell_skin(current_price, list_of_assets, cookies)
            logs[skin] = {
                "my_sell_price": round(current_price, 2),
                "margin+": margin,
                "timestamp_when_placed_to_sell": datetime.now().isoformat()
            }

        save_data(logs, "/home/pustrace/programming/trade/steam/database/logs.json")

    
    print("Sell is complite.")