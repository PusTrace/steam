# tests/generators.py

import random
from datetime import datetime, timedelta, timezone

from core.objects import (
    ItemMarketData,
    ItemOrder,
    ItemPriceHistory,
    Skin,
)


def generate_price_history(days: int = 30):

    history = []

    base_price = random.uniform(100, 1000)

    for i in range(days):

        price = round(
            base_price + random.uniform(-50, 50),
            2,
        )

        history.append(
            ItemPriceHistory(
                date=datetime.now(timezone.utc) - timedelta(days=i),
                price=price,
                volume=random.randint(1, 100),
            )
        )

    return history


def generate_orders(count: int = 10):

    orders = []

    for _ in range(count):
        orders.append(
            ItemOrder(
                price=round(random.uniform(100, 1000), 2),
                qty=random.randint(1, 20),
            )
        )

    return orders


def generate_market_data():

    skin = Skin(
        id=1,
        name="Fake Skin",
        item_name_id=123456,
    )

    return ItemMarketData(
        history=generate_price_history(),
        buy_orders=generate_orders(),
        sell_orders=generate_orders(),
        skin=skin,
    )
