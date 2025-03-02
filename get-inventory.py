import requests
import json
import os

# URL для получения инвентаря
url = f'https://steamcommunity.com/profiles/76561198857946351/inventory/json/730/2/?l=english'

# Создание сессии
session = requests.Session()

# Куки, которые вы передали
cookies = {
    'steamLoginSecure': os.getenv("STEAM_LOGIN_SECURE"),
}

# Добавление куков в сессию
session.cookies.update(cookies)

# Заголовки для имитации запроса из браузера
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
}

# Выполнение запроса с сессией, куками и заголовками
response = session.get(url, headers=headers)
print(response)

# Проверка на успешность ответа
if response.status_code == 200:
    data = response.json()

    # Чтение данных из файла, если он существует
    try:
        with open('/home/pustrace/programming/trade/steam/database/timer.json', 'r') as file:
            skins_data = json.load(file)
    except FileNotFoundError:
        skins_data = {}

    # Извлечение market_hash_name, cache_expiration и текущего времени
    for item in data['rgDescriptions'].values():
        market_hash_name = item['market_hash_name']

        # Проверка на наличие cache_expiration
        cache_expiration = item.get('cache_expiration', None)

        # Проверка, существует ли уже такой скин в данных
        if market_hash_name not in skins_data:
            skins_data[market_hash_name] = {}

        skins_data[market_hash_name]['cache_expiration'] = cache_expiration

    # Сохранение обновленных данных в файл
    with open('/home/pustrace/programming/trade/steam/database/timer.json', 'w') as file:
        json.dump(skins_data, file, indent=4)

else:
    print(f"Ошибка {response.status_code}")
