from selenium_stealth import stealth
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
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
    # Проверяем: если есть свежие куки — просто загружаем
    cached_cookies = load_cookies_if_fresh()
    if cached_cookies:
        print("[INFO] Загружаем куки из кэша")
        driver_headless = setup_driver(headless=True)
        load_cookies(driver_headless, cached_cookies)
        return cached_cookies, driver_headless

    # Иначе авторизуемся
    print("[INFO] Авторизация в Steam...")
    driver_normal = setup_driver(headless=False)
    steam_login(driver_normal)
    cookies = driver_normal.get_cookies()
    driver_normal.quit()

    # Сохраняем куки с меткой времени
    save_cookies_with_timestamp(cookies)

    # Загружаем в headless-драйвер
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