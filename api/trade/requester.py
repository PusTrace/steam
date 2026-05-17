import requests, time, random, re
from urllib.parse import urlencode, quote
from playwright.sync_api import Page

def buy_skin_by_listing_id(session, listing_id, price, price_without_fee, sessionid):
    """Покупка предмета по listing_id."""
    fee = round((price - price_without_fee) * 100)
    total = round(price * 100)
    subtotal = round(price_without_fee * 100)

    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Referer": "https://steamcommunity.com/market/",
        "Origin": "https://steamcommunity.com",
        "User-Agent": "Mozilla/5.0"
    }

    data = {
        "sessionid": sessionid,
        "currency": "1",
        "subtotal": subtotal,
        "fee": fee,
        "total": total,
        "quantity": 1
    }

    url = f"https://steamcommunity.com/market/buylisting/{listing_id}"
    resp = session.post(url, data=urlencode(data), headers=headers)
    print("📦 Ответ покупки:", resp.status_code, resp.text[:500])
    if resp.status_code == 406 and "need_confirmation" in resp.text:
        print("⚠️ Требуется подтверждение в мобильном приложении")
    elif "success" in resp.text:
        print("✅ Покупка успешна")
    else:
        print("❌ Ошибка покупки")
        
        
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

    response = session.post(url, headers=headers, cookies=cookies, data=data, timeout=30)
    if response.status_code == 400:
        time.sleep(random.uniform(4, 8))

    return response


def get_item_nameid_with_page(skin_name: str, page: Page) -> tuple[int, float | None]:
    """
    Возвращает:
        (item_nameid, avg_price)

    item_nameid:
        >0  — найден
        -1  — нет листингов
        0   — Market_LoadOrderSpread не найден

    avg_price:
        средняя цена по DOM или None
    """
    url = "https://steamcommunity.com/market/listings/730/" + quote(skin_name, safe="")

    page.goto(url, wait_until="networkidle")

    # ждём либо скрипт, либо сообщение о пустом листинге
    try:
        page.wait_for_function(
            """
            () =>
                [...document.scripts].some(s => s.textContent.includes('Market_LoadOrderSpread')) ||
                document.querySelector('.market_listing_table_message') !== null
            """,
            timeout=15000
        )
    except:
        pass

    # === проверка "нет листингов"
    no_listing = page.query_selector(".market_listing_table_message")
    if no_listing:
        text = no_listing.inner_text().strip()
        if "There are no listings" in text:
            return -1, None

    # === собираем цены из DOM
    price_elements = page.query_selector_all(
        "span.market_listing_price.market_listing_price_with_fee"
    )
    prices: list[float] = []

    for el in price_elements:
        raw = el.inner_text().strip()
        text = raw.replace(" ", "").replace("\n", "")
        m = re.search(r"(\d+)", text)
        if not m:
            return None

        value = int(m.group(1))

        # ₸, ₽, ¥ — без копеек → делим на 100
        if "₸" in text or "₽" in text:
            value / 100

        price = float(value)

        prices.append(price)


    avg_price = sum(prices) / len(prices) if prices else None

    # === ищем item_nameid
    html = page.content()
    m = re.search(r"Market_LoadOrderSpread\(\s*(\d+)\s*\)", html)
    if m:
        return int(m.group(1)), avg_price

    return 0, avg_price
