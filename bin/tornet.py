import requests
import time
import stem.control
from stem import Signal
import os

TOR_CONTROL_PORT = 9051
TOR_SOCKS_PROXY = "socks5h://127.0.0.1:9050"
TOR_PASSWORD = os.getenv("TOR_NET")

def get_ip():
    """Получает текущий внешний IP через Tor"""
    try:
        response = requests.get("http://httpbin.org/ip", proxies={"http": TOR_SOCKS_PROXY, "https": TOR_SOCKS_PROXY})
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def change_ip():
    """Запрашивает новый IP через Tor"""
    try:
        with stem.control.Controller.from_port(port=TOR_CONTROL_PORT) as controller:
            controller.authenticate(password=TOR_PASSWORD)
            controller.signal(Signal.NEWNYM)  # Запрос смены IP
    except Exception as e:
        print(f"Ошибка смены IP: {e}")

if __name__ == "__main__":
    print("IP до смены:", get_ip())
    change_ip()
    time.sleep(10)  # Даем Tor время сменить IP
    print("IP после смены:", get_ip())
