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


def authorize_and_get_cookies():
    cached_cookies = load_cookies_if_fresh()
    if cached_cookies:
        print("[INFO] Загружаем куки из кэша")
        driver_headless = setup_driver(headless=True)
        load_cookies(driver_headless, cached_cookies)
        return cached_cookies, driver_headless

    print("[INFO] Авторизация в Steam...")
    driver_normal = setup_driver(headless=False)
    steam_login(driver_normal)
    cookies = driver_normal.get_cookies()
    driver_normal.quit()

    save_cookies_with_timestamp(cookies)
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
