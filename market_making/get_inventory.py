import requests
import json
import os
import sys

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
from utils.utils import save_data


url = f'https://steamcommunity.com/profiles/76561198857946351/inventory/json/730/2/?l=english'
session = requests.Session()
cookies = {
    'steamLoginSecure': os.getenv("STEAM_LOGIN_SECURE"),
}
session.cookies.update(cookies)
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
}
response = session.get(url, headers=headers)
if response.status_code == 200:
    data = response.json()
    with open('/home/pustrace/programming/trade/steam/database/timer.json', 'r') as file:
        skins_data = json.load(file)

    # Извлечение market_hash_name, cache_expiration и текущего времени
    for item in data['rgDescriptions'].values():
        market_hash_name = item['market_hash_name']

        # Проверка на наличие cache_expiration
        cache_expiration = item.get('cache_expiration', None)
        skins_data[market_hash_name] = {'cache_expiration': cache_expiration}

        save_data(skins_data, '/home/pustrace/programming/trade/steam/database/timer.json')

else:
    print(f"Ошибка {response.status_code}")
