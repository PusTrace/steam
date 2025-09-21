from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException
import time
import os
import pickle
import urllib.parse
import requests
from bs4 import BeautifulSoup

def steam_login(driver):
    login_url = "https://steamcommunity.com/login/home/"
    driver.get(login_url)
    WebDriverWait(driver, 99999999999).until(
        EC.presence_of_element_located((By.CLASS_NAME, "actual_persona_name"))
    )
    print("Авторизация в Steam выполнена.")


def setup_driver(headless=True):
    options = Options()
    if headless:
        options.headless = True

    # Создаем профиль и настраиваем его
    profile = FirefoxProfile()
    profile.set_preference("dom.webdriver.enabled", False)
    profile.set_preference("useAutomationExtension", False)
    profile.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0")
    profile.set_preference("privacy.resistFingerprinting", True)
    profile.set_preference("webgl.disabled", True)
    profile.set_preference("media.navigator.enabled", False)
    profile.update_preferences()

    # ВАЖНО: передаем профиль через options
    options.profile = profile

    driver = webdriver.Firefox(options=options)
    return driver


def load_cookies(driver, cookies):
    driver.get("https://steamcommunity.com/")
    for cookie in cookies:
        if 'expiry' in cookie:
            cookie.pop('expiry')
        driver.add_cookie(cookie)
    driver.refresh()


def save_cookies_with_timestamp(cookies):
    data = {
        "timestamp": time.time(),
        "cookies": cookies
    }
    with open("steam_cookies.pkl", "wb") as f:
        pickle.dump(data, f)


def load_cookies_if_fresh():
    if not os.path.exists("steam_cookies.pkl"):
        return None
    with open("steam_cookies.pkl", "rb") as f:
        data = pickle.load(f)
    timestamp = data.get("timestamp", 0)
    if time.time() - timestamp < 24 * 3600:
        return data["cookies"]
    return None


def authorize_and_get_cookies(only_cookies=False):
    cached_cookies = load_cookies_if_fresh()
    if cached_cookies:
        if only_cookies:
            return cached_cookies
        driver_headless = setup_driver(headless=True)
        load_cookies(driver_headless, cached_cookies)
        return cached_cookies, driver_headless

    print("[INFO] Авторизация в Steam...")
    driver_normal = setup_driver(headless=False)
    steam_login(driver_normal)
    cookies = driver_normal.get_cookies()
    driver_normal.quit()
    
    save_cookies_with_timestamp(cookies)
    if only_cookies:
        return cookies
    else:    
        driver_headless = setup_driver(headless=True)
        load_cookies(driver_headless, cookies)
        return cookies, driver_headless


def buy_skin(driver, skin, y, number_of_items):
    wait = WebDriverWait(driver, 10)
    url = generate_steam_market_url(skin)
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
        price_for_skin.send_keys(y)
        time.sleep(0.5)

        item_quantity = wait.until(EC.presence_of_element_located(
            (By.ID, "market_buy_commodity_input_quantity")
        ))
        item_quantity.clear()
        item_quantity.send_keys(number_of_items)
        time.sleep(0.5)

        ssa_input = wait.until(EC.presence_of_element_located(
            (By.ID, "market_buyorder_dialog_accept_ssa")
        ))
        ssa_input.click()
        time.sleep(0.5)

        btn_to_complite = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "#market_buyorder_dialog_purchase > span")
        ))
        time.sleep(0.5)
        btn_to_complite.click()
        time.sleep(2.5)
    except TimeoutException:
        print("Timeout: Элементы не найдены")
        return
    except Exception as e:
        print("Ошибка:", e)
        driver.quit()


def generate_steam_market_url(item_name: str) -> str:
    base_url = "https://steamcommunity.com/market/listings/730/"
    encoded_name = urllib.parse.quote(item_name)
    return base_url + encoded_name


def get_inventory(cookies_from_browser):
    """
    return a dictionary like this: {name: {marketable, classid, instanceid, asset_ids: [], marketable_time}}
    """
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
            owner_descriptions = item.get('owner_descriptions')
            marketable_time = owner_descriptions[1].get('value') if owner_descriptions is not None else None

            asset_ids = []

            for asset_item in asset_data_list:
                if classid == asset_item.get('classid') and instanceid == asset_item.get('instanceid'):
                    asset_ids.append(asset_item.get('assetid'))
            
            # Записываем собранные данные в skins_data
            skins_data[market_hash_name] = {
                'marketable': marketable,
                'classid': classid,
                'instanceid': instanceid,
                'asset_ids': asset_ids,
                'marketable_time': marketable_time
            }
            

        return skins_data
    else:
        print(f"Ошибка запроса инвентаря: статус {response.status_code}")
   

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


def sell_skin(price, list_of_assets, cookies):
    """
    place a sell order for each asset in list_of_assets at the given price
    """
    url = "https://steamcommunity.com/market/sellitem/"
    price_for_steam = round(price * 100 *0.87)

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
            return True
        else:
            return False


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

