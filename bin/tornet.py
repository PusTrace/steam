import requests
import time
import stem.control
from stem import Signal
import os

def get_ip():
    """Получает текущий внешний IP через Tor"""
    try:
        response = requests.get("https://icanhazip.com", proxies={"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"})
        return response.text
    except Exception as e:
        return {"error": str(e)}

def change_ip():
    """Запрашивает новый IP через Tor"""
    try:
        with stem.control.Controller.from_port(port=9051) as controller:
            controller.authenticate(password=os.getenv("TOR_NET"))
            controller.signal(Signal.NEWNYM)  # Запрос смены IP
    except Exception as e:
        print(f"Ошибка смены IP: {e}")

if __name__ == "__main__":
    print("IP до смены:", get_ip())
    change_ip()
    time.sleep(10)  # Даем Tor время сменить IP
    print("IP после смены:", get_ip())
