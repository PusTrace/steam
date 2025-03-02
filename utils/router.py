import requests
import os

# Параметры
ROUTER_IP = "192.168.0.1"
USERNAME = "PusTrace"
PASSWORD = os.getenv("YOUR_PASSWORD")

# Создаем сессию
session = requests.Session()

# Заголовки
session.headers.update({
    "Accept": "*/*",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
    "Content-Type": "text/plain",
    "Origin": f"http://{ROUTER_IP}",
    "Referer": f"http://{ROUTER_IP}/mainFrame.htm",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Cookie": "Authorization=Basic UHVzVHJhY2U6U3RhbGtlcjIwMDUyMg=="
})

# Данные запроса
data = '[ACT_REBOOT#0,0,0,0,0,0#0,0,0,0,0,0]0,0\r\n'

# Отправка запроса
response = session.post(f'http://{ROUTER_IP}/cgi?7', data=data, verify=False)

# Проверка ответа
if response.status_code == 200:
    print("Роутер успешно перезагружен! (проверь вручную)")
else:
    print(f"Ошибка! Код ответа: {response.status_code}")
    print(response.text)
