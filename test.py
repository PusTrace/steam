import requests
import os
import json

def get_inventory(steam_cookie=None):
    url = 'https://steamcommunity.com/inventory/76561198857946351/730/2'
    session = requests.Session()
    
    # Если кука не передана, берем из переменных окружения
    if steam_cookie is None:
        steam_cookie = os.getenv("STEAM_LOGIN_SECURE")
        if steam_cookie is None:
            print("Ошибка: не найдена кука steamLoginSecure ни в параметрах, ни в переменных окружения!")
            return

    cookies = {'steamLoginSecure': steam_cookie}
    session.cookies.update(cookies)
    
    headers = {
        'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/58.0.3029.110 Safari/537.36')
    }
    
    response = session.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()

        # Загружаем сохранённые данные скинов
        with open('/home/pustrace/programming/trade/steam/database/inventory.json', 'r') as file:
            skins_data = json.load(file)

        # Получаем списки assets и описаний
        assets = data.get('assets', [])
        descriptions = data.get('descriptions', [])

        # Собираем все данные по asset'ам в список
        asset_data_list = []
        for asset in assets:
            asset_info = {
                "assetid": asset.get('assetid'),
                "classid": asset.get('classid'),
                "instanceid": asset.get('instanceid')
            }
            asset_data_list.append(asset_info)

        # Проходим по описаниям и ищем в asset_data_list совпадения по classid и instanceid
        for item in descriptions:
            market_hash_name = item.get('market_hash_name')
            marketable = item.get('marketable')
            classid = item.get('classid')
            instanceid = item.get('instanceid')
            asset_ids = []

            for asset_item in asset_data_list:
                if classid == asset_item.get('classid') and instanceid == asset_item.get('instanceid'):
                    asset_ids.append(asset_item.get('assetid'))
            
            # Записываем собранные данные в skins_data
            skins_data[market_hash_name] = {
                'marketable': marketable,
                'classid': classid,
                'instanceid': instanceid,
                'asset_ids': asset_ids
            }
        
    else:
        print(f"Ошибка запроса инвентаря: статус {response.status_code}")
        
        
#main code
get_inventory()