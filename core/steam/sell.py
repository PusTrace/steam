import requests, logging

log = logging.getLogger("sell_skins")

def sell_skin(price, asset_id, cookies):
    """
    place a sell order of asset at the given price
    """
    log.debug(f"type_price:{type(price)}")
    url = "https://steamcommunity.com/market/sellitem/"
    price_for_steam = round(price * 100 *0.87)

    session = requests.Session()

 # Закидываем ВСЕ куки в сессию
    session.cookies.update(cookies)

    # Вытаскиваем sessionid из куков
    sessionid = cookies.get("sessionid")
    if not sessionid:
        raise Exception("❌ sessionid не найден в cookies")

    headers = {
        "Host": "steamcommunity.com",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:146.0) Gecko/20100101 Firefox/146.0",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://steamcommunity.com",
        "Referer": "https://steamcommunity.com/profiles/76561198857946351/inventory",
        "Dnt": "1"
    }

    
    data = {
        "sessionid": sessionid,
        "appid": "730",
        "contextid": "2",
        "assetid": asset_id,
        "amount": 1,
        "price": price_for_steam
    }
    response = session.post(url, headers=headers, data=data)

    answer = response.json()
    success = answer.get('success')
    if not success:
        log.error(answer)
    return bool(success)