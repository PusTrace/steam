import requests
import os
import base64

# Параметры
ROUTER_IP = "192.168.0.1"
USERNAME = "PusTrace"
PASSWORD = os.getenv("DEFAULT_PASSWORD")

# Создаем сессию
session = requests.Session()

# Заголовки
auth_str = f"{USERNAME}:{PASSWORD}"
auth_b64 = base64.b64encode(auth_str.encode()).decode()

session.headers.update({
    "Accept": "*/*",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
    "Content-Type": "text/plain",
    "Origin": f"http://{ROUTER_IP}",
    "Referer": f"http://{ROUTER_IP}/mainFrame.htm",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Cookie": f"Authorization=Basic {auth_b64}"
})

# Данные запроса
data = '[ACT_REBOOT#0,0,0,0,0,0#0,0,0,0,0,0]0,0\r\n'

# Отправка запроса
response = session.post(f'http://{ROUTER_IP}/cgi?7', data=data, verify=False)

# Проверка ответа
if response.status_code == 200:
    print("Роутер успешно перезагружен!")
else:
    print(f"Ошибка! Код ответа: {response.status_code}")
    print(response.text)
