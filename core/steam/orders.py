import requests
from bs4 import BeautifulSoup
def cancel_order(skin, buy_order_id, cookies):
    """Отменяет ордер на покупку скина."""
    url = "https://steamcommunity.com/market/cancelbuyorder/"  # исправил URL
    session = requests.Session()

    # Закидываем ВСЕ куки в сессию
    for cookie in cookies:
        session.cookies.set(cookie['name'], cookie['value'])

    # Вытаскиваем sessionid из куков
    sessionid = None
    for cookie in cookies:
        if cookie['name'] == 'sessionid':
            sessionid = cookie['value']
            break

    headers = {
        "Host": "steamcommunity.com",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:137.0) Gecko/20100101 Firefox/137.0",
        "Accept": "text/javascript, text/html, application/xml, text/xml, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "X-Prototype-Version": "1.7",
        "Origin": "https://steamcommunity.com",
        "Referer": "https://steamcommunity.com/market/",
        "Dnt": "1",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Te": "trailers",
        "Connection": "close"
    }

    data = {
        "sessionid": sessionid,
        "buy_orderid": buy_order_id
    }

    response = session.post(url, headers=headers, data=data)

    if response.status_code == 200:
        print(f"skin {skin} успешно убран из стенки. Ответ: {response.text}")
    else:
        print(f"Ошибка при попытке убрать skin {skin}: {response.status_code}\nОтвет: {response.text}")



