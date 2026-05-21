"""
tests/test_parser.py

Тесты parser.py — читают данные из tests/outputs/ (сохранённые test_client.py).
Никаких сетевых запросов.

Запуск:
    pytest tests/test_parser.py -v
"""

import json
import pytest
from pathlib import Path
from datetime import datetime
from dataclasses import asdict

from api.market import parser
from api.market.models import (
    ItemPriceHistory,
    ItemOrder,
    UserInventory,
    UserBuyOrder,
    UserSellOrder,
    UserHistory,
)

OUTPUTS_DIR = Path(__file__).parent / "outputs"


def skin_to_filename(skin_name: str) -> str:
    return skin_name.replace(" ", "_").replace("|", "").replace("/", "")


def save(filename: str, data):
    path = OUTPUTS_DIR / filename
    if isinstance(data, dict):
        serialized = {
            k: [
                asdict(i) if hasattr(i, "__dataclass_fields__") else i.__dict__
                for i in v
            ]
            for k, v in data.items()
        }
    elif isinstance(data, list):
        serialized = [
            asdict(i) if hasattr(i, "__dataclass_fields__") else i.__dict__
            for i in data
        ]
    path.write_text(json.dumps(serialized, indent=2, ensure_ascii=False, default=str))


# ═══════════════════════════════════════════════════════════════════ #
#  extract_price_history + parse_price_history                        #
# ═══════════════════════════════════════════════════════════════════ #


@pytest.mark.parametrize(
    "skin_name",
    [
        "USP-S | Blueprint (Well-Worn)",
        "M4A1-S | Flashback (Field-Tested)",
        "USP-S | Whiteout (Factory New)",
    ],
)
def test_parse_price_history(skin_name):
    safe = skin_to_filename(skin_name)
    html = (OUTPUTS_DIR / f"history_{safe}.html").read_text(encoding="utf-8")

    raw = parser.extract_price_history(html)
    assert isinstance(raw, dict)
    assert skin_name in raw

    histories = parser.parse_price_history(raw)
    assert isinstance(histories, dict)
    assert skin_name in histories

    history = histories[skin_name]
    assert len(history) > 0

    for item in history:
        assert isinstance(item, ItemPriceHistory)
        assert isinstance(item.price, float) and item.price > 0
        assert isinstance(item.volume, int) and item.volume >= 0
        assert isinstance(item.date, datetime)

    save(f"parsed_price_history_{safe}.json", histories)


# ═══════════════════════════════════════════════════════════════════ #
#  parse_orders                                                       #
# ═══════════════════════════════════════════════════════════════════ #


@pytest.mark.parametrize(
    "skin_name",
    [
        "USP-S | Blueprint (Well-Worn)",
        "M4A1-S | Flashback (Field-Tested)",
        "USP-S | Whiteout (Factory New)",
    ],
)
def test_parse_orders(skin_name):
    safe = skin_to_filename(skin_name)
    data = json.loads((OUTPUTS_DIR / f"orders_{safe}.json").read_text())

    buy, sell = parser.parse_orders(data)

    assert isinstance(buy, list) and len(buy) > 0
    assert isinstance(sell, list) and len(sell) > 0

    for order in buy:
        assert isinstance(order, ItemOrder)
        assert order.price > 0
        assert order.qty > 0

    for order in sell:
        assert isinstance(order, ItemOrder)
        assert order.price > 0
        assert order.qty > 0

    save(f"parsed_orders_{safe}.json", buy + sell)


# ═══════════════════════════════════════════════════════════════════ #
#  parse_inventory                                                    #
# ═══════════════════════════════════════════════════════════════════ #


def test_parse_inventory():
    data = json.loads((OUTPUTS_DIR / "inventory.json").read_text())

    inventory = parser.parse_inventory(data)

    assert isinstance(inventory, list)

    if not inventory:
        pytest.skip("Инвентарь пустой — нечего проверять")

    for item in inventory:
        assert isinstance(item, UserInventory)
        assert isinstance(item.name, str) and item.name
        assert item.class_id is not None
        assert item.instance_id is not None
        assert item.asset_id is not None

    save("parsed_inventory.json", inventory)


# ═══════════════════════════════════════════════════════════════════ #
#  parse_my_market_page                                               #
# ═══════════════════════════════════════════════════════════════════ #


def test_parse_my_market_page():
    html = (OUTPUTS_DIR / "my_market_page.html").read_text(encoding="utf-8")

    total, wallet, buy_orders, sell_orders = parser.parse_my_market_page(html)

    assert isinstance(total, float)
    assert isinstance(wallet, float)
    assert isinstance(buy_orders, list)
    assert isinstance(sell_orders, list)

    for order in buy_orders:
        assert isinstance(order, UserBuyOrder)
        assert order.price > 0
        assert order.qty > 0
        assert isinstance(order.name, str)

    for order in sell_orders:
        assert isinstance(order, UserSellOrder)
        assert order.price > 0
        assert isinstance(order.name, str)

    (OUTPUTS_DIR / "parsed_my_state.json").write_text(
        json.dumps(
            {
                "total_buyorders": total,
                "wallet_balance": wallet,
                "buy_orders": [asdict(o) for o in buy_orders],
                "sell_orders": [asdict(o) for o in sell_orders],
            },
            indent=2,
            ensure_ascii=False,
        )
    )


# ═══════════════════════════════════════════════════════════════════ #
#  parse_my_history                                                   #
# ═══════════════════════════════════════════════════════════════════ #


@pytest.mark.parametrize("start,count", [(0, 10), (0, 50)])
def test_parse_my_history(start, count):
    data = json.loads((OUTPUTS_DIR / f"my_history_{start}_{count}.json").read_text())

    history, total_count = parser.parse_my_history(data)

    assert isinstance(history, list)
    assert isinstance(total_count, int)

    if not history:
        pytest.skip("История пустая — нечего проверять")

    for item in history:
        assert isinstance(item, UserHistory)
        assert item.asset_id is not None
        assert isinstance(item.name, str)
        assert item.price > 0
        assert isinstance(item.gain_loss, bool)

    save(f"parsed_my_history_{start}_{count}.json", history)
