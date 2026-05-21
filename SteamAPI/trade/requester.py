import re
from urllib.parse import quote
from playwright.sync_api import Page


def get_item_nameid_with_page(
    skin_name: str, page: Page
) -> tuple[int, float | None] | None:
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
    page.wait_for_function(
        """
        () =>
            [...document.scripts].some(s => s.textContent.includes('Market_LoadOrderSpread')) ||
            document.querySelector('.market_listing_table_message') !== null
        """,
        timeout=15000,
    )

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
