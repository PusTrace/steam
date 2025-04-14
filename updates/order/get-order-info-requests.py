import requests

url = "https://steamcommunity.com/market/itemordershistogram?country=KZ&language=russian&currency=37&item_nameid=2393050"
response = requests.get(url)

if response.status_code == 200:
    data = response.json()
    print(data)
else:
    print("Не удалось получить данные")

