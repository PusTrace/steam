from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import Select
import time
import json
import re
import signal
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from steam.utils.utils import generate_market_url,  check_skin_in_database, save_data, signal_handler, run_router_script

def get_orders_data(url, keep_browser_open=False):
    """
    Открывает страницу, кликает по нужным элементам и извлекает информацию.
    Возвращает список строк с информацией.
    """

    wait = WebDriverWait(driver, 10)
    
    try:
        driver.get(url)
        consecutive_errors = 0

        while consecutive_errors < max_attempts:
            try:
                span_button = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div[7]/div[2]/div[2]/div[4]/div[1]/div[3]/div[3]/div[1]/div[2]/div[2]/span")))
                driver.execute_script("arguments[0].click();", span_button)
                print("Клик по span выполнен")
                wait.until(EC.invisibility_of_element(span_button))  # Используем для ожидания исчезновения кнопки span
                print("Кнопка span исчезла, можно переходить к следующему шагу.")
                break
            except Exception as e:
                print("Ошибка при клике на span:", e)
                time.sleep(300)
                consecutive_errors += 1
                driver.refresh()
                if consecutive_errors >= max_attempts:
                    print("Превышено количество ошибок подряд. Запускаем router.py...")
                    run_router_script()
                    print(consecutive_errors)
                    consecutive_errors = 0
                    driver.refresh()
        
        # Пример: выбор значения в select
        try:
            select_element = wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[7]/div[2]/div[2]/div[4]/div[1]/div[3]/div[3]/div[2]/div/div[1]/div[1]/div[1]/select")))
            select = Select(select_element)
            select.select_by_index(35)
            print("Элемент select обновлён")
        except Exception as e:
            print("Ошибка при выборе значения в select:", e)
        
        time.sleep(1)
        # Пример: клик по ссылке
        try:
            link_button = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div[7]/div[2]/div[2]/div[4]/div[1]/div[3]/div[3]/div[2]/div/div[2]/div[1]/div[1]/a")))
            driver.execute_script("arguments[0].click();", link_button)
            print("Клик по ссылке выполнен")
        except Exception as e:
            print("Ошибка при клике на ссылку:", e)
        
        
        # Извлекаем данные из нужного элемента
        time.sleep(4)
        data_element = wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[7]/div[2]/div[2]/div[4]/div[1]/div[3]/div[3]/div[2]/div/div[1]/div[1]")))
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
            driver.close()  # Закрыть вкладку только если флаг не активен
        driver.switch_to.window(driver.window_handles[0])  # Переключаемся обратно на первую вкладку
        return parsed_data
    except Exception as e:
        print(f"Ошибка при получении данных: {e}")
        return []
    finally:
        if not keep_browser_open:
            driver.quit()  # Закрытие всех вкладок и завершение работы браузера

if __name__ == "__main__":
    options = webdriver.ChromeOptions()
    options.add_extension("extensions/steam_invenory_helper2.3.1_0.crx")
    
    service = Service()  # Если необходимо, можно указать путь к chromedriver
    driver = webdriver.Chrome(service=service, options=options)

    # Регистрируем обработчик сигнала (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)
    
    with open("/steam/database/database.json", 'r', encoding='utf-8') as f:
        skins = json.load(f)
    try:
        with open("/steam/database/orders_data.json", 'r', encoding='utf-8') as f:
            skin_data = json.load(f)
    except Exception as e:
        skin_data = {}
    
    consecutive_errors = 0  # Счётчик ошибок 429 подряд
    max_attempts = 6

    for skin in skins:
        if check_skin_in_database(skin, skin_data):
            print(f"Данные для '{skin}' уже существуют, пропускаем запрос.")
            continue

        url = generate_market_url(skin)

        print(f"\nПолучение данных для '{skin}'...")
        orders_data = get_orders_data(url, keep_browser_open=True)
        
        if orders_data:
            skin_data[skin] = orders_data
            save_data({skin: orders_data}, filename="steam/database/orders_data.json")
            print(f"Данные ордеров для '{skin}' успешно получены и сохранены.")
            consecutive_errors = 0
        else:
            print(f"Ошибка при получении данных для '{skin}'. Пропускаем.")
            consecutive_errors += 1
            if consecutive_errors > max_attempts:
                print("Превышено количество ошибок подряд. Запускаем router.py...")
                run_router_script()
                print(consecutive_errors)
                consecutive_errors = 0

    print("Парсинг завершён.")
