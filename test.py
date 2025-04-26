from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth
import requests
from bs4 import BeautifulSoup

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


import requests
from bs4 import BeautifulSoup

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
    with open("response.html", "w", encoding="utf-8") as file:
        file.write(response.text)
    if response.status_code == 200:
        print("Запрос выполнен успешно.")
        soup = BeautifulSoup(response.text, "html.parser")
        
        orders = soup.find_all("div", id=lambda x: x and x.startswith("mybuyorder_"))

        for order_div in orders:
            order_id_full = order_div.get("id")
            order_id = order_id_full.split("_")[1]

            item_name_tag = order_div.find("a", class_="market_listing_item_name_link")
            if item_name_tag:
                item_name = item_name_tag.text.strip()
                print(f"OrderID: {order_id} | Название предмета: {item_name}")
            else:
                print(f"OrderID: {order_id} | Название предмета не найдено.")
    else:
        print(f"Ошибка запроса: {response.status_code}")



if __name__ == "__main__":
    driver_normal = setup_driver(headless=False)
    steam_login(driver_normal)
    cookies = driver_normal.get_cookies()
    driver_normal.quit()
    my_list_information = get_list_of_my_orders(cookies)