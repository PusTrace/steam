import requests
from bs4 import BeautifulSoup


def cancel_order(skin, buy_order_id, cookies):
    """Отменяет ордер на покупку скина."""
    url = "https://steamcommunity.com/market/cancelbuyorder/"  # исправил URL
    session = requests.Session()

    # Закидываем ВСЕ куки в сессию
    for cookie in cookies:
        session.cookies.set(cookie["name"], cookie["value"])

    # Вытаскиваем sessionid из куков
    sessionid = None
    for cookie in cookies:
        if cookie["name"] == "sessionid":
            sessionid = cookie["value"]
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
        "Connection": "close",
    }

    data = {"sessionid": sessionid, "buy_orderid": buy_order_id}

    response = session.post(url, headers=headers, data=data)

    if response.status_code == 200:
        print(f"skin {skin} успешно убран из стенки. Ответ: {response.text}")
    else:
        print(
            f"Ошибка при попытке убрать skin {skin}: {response.status_code}\nОтвет: {response.text}"
        )


def create_buy_order(cookies, market_hash_name, price, quantity, confirmation_id=0):
    session = requests.Session()
    encoded_name = quote(market_hash_name)

    url = "https://steamcommunity.com/market/createbuyorder/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/118.0.5993.118 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": f"https://steamcommunity.com/market/listings/730/{encoded_name}",
        "Origin": "https://steamcommunity.com",
        "Connection": "keep-alive",
        "X-Requested-With": "XMLHttpRequest",
    }

    sessionid = cookies.get("sessionid")

    data = {
        "sessionid": sessionid,
        "currency": "37",
        "appid": "730",
        "market_hash_name": market_hash_name,
        "price_total": str(int(price * quantity * 100)),
        "quantity": str(quantity),
        "confirmation": confirmation_id,
    }

    response = session.post(
        url, headers=headers, cookies=cookies, data=data, timeout=30
    )
    if response.status_code == 400:
        time.sleep(random.uniform(4, 8))

    return response
