import time
import json
import subprocess
import sys
import urllib.parse


def generate_market_url(skin_name):
    """Генерирует URL для скина на маркете Steam."""
    encoded_name = urllib.parse.quote(skin_name)
    url = f"https://steamcommunity.com/market/listings/730/{encoded_name}"
    return url
    
def check_skin_in_database(skin, skin_data):
    """Проверяет, есть ли данные о скине в базе данных."""
    if skin in skin_data:
        return True
    return False

def save_data(new_data, filename):
    """Сохраняет или обновляет данные в JSON файле."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
           existing_data = json.load(f)
        if not existing_data:
            existing_data = {}
        for key, value in new_data.items():
            if key in existing_data:
                if isinstance(existing_data[key], list):
                    existing_data[key].append(value)
                elif isinstance(existing_data[key], dict):
                    existing_data[key].update(value)
                else:
                    existing_data[key] = [existing_data[key], value]
            else:
                existing_data[key] = value
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=4)
        print(f"Данные успешно сохранены в {filename}")
    except Exception as e:
        print(f"Ошибка при сохранении данных: {e}")
        
    
def signal_handler(signum, frame):
    """Обработчик сигнала прерывания."""
    global skin_data
    print("\nПолучен сигнал прерывания. Сохраняем данные перед выходом...")
    if 'skin_data' in globals() and skin_data:
        save_data(skin_data)
    print("Данные сохранены. Завершение работы.")
    sys.exit(0)

def run_router_script():
    """Запускает router.py."""
    try:
        subprocess.run(["python", "/home/pustrace/programming/steam_parser/utils/router.py"], check=True)
        print("router.py успешно запущен.")
        print("Ожидаем 5 минут...")
        time.sleep(300)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при запуске router.py: {e}")