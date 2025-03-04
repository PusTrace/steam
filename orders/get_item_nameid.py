import requests
from bs4 import BeautifulSoup
import re

# URL страницы с листингом предмета
url = "https://steamcommunity.com/market/listings/730/USP-S%20%7C%20Check%20Engine%20%28Minimal%20Wear%29"
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

# Ищем все скриптовые теги
scripts = soup.find_all('script')
item_nameid = None
for script in scripts:
    if script.string and 'item_nameid' in script.string:
        # Пример регулярного выражения для поиска item_nameid
        match = re.search(r'item_nameid\s*[:=]\s*["\']?(\d+)', script.string)
        if match:
            item_nameid = match.group(1)
            break

if item_nameid:
    print("Item NameID:", item_nameid)
else:
    print("Не удалось найти item_nameid")
