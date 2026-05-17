"""
tests/test_client.py

Интеграционные тесты client.py — реальные запросы к Steam.
Сырые ответы сохраняются в tests/outputs/ для последующего использования в test_parser.py.

Запуск:
    pytest tests/test_client.py -v
"""

import json
import pytest
from pathlib import Path

import time
import random
from tests.conftest import TEST_SKIN_NAMES

OUTPUTS_DIR = Path(__file__).parent / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)


@pytest.fixture(autouse=True)
def rate_limit():
    yield
    time.sleep(random.uniform(3, 6))


# ═══════════════════════════════════════════════════════════════════ #
#  fetch_orders                                                       #
# ═══════════════════════════════════════════════════════════════════ #


@pytest.mark.parametrize("skin_name", TEST_SKIN_NAMES)
def test_fetch_orders(client, db, skin_name):
    from core.objects import Skin

    skin = Skin.model_validate(db.get_test_skin(skin_name))

    data = client.fetch_orders(skin.item_name_id)

    assert isinstance(data, dict)
    assert "buy_order_graph" in data
    assert "sell_order_graph" in data
    assert isinstance(data["buy_order_graph"], list)
    assert isinstance(data["sell_order_graph"], list)

    safe_name = skin_name.replace(" ", "_").replace("|", "").replace("/", "")
    path = OUTPUTS_DIR / f"orders_{safe_name}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


# ═══════════════════════════════════════════════════════════════════ #
#  fetch_price_history_html                                           #
# ═══════════════════════════════════════════════════════════════════ #


@pytest.mark.parametrize("skin_name", TEST_SKIN_NAMES)
def test_fetch_price_history_html(client, skin_name):
    html = client.fetch_price_history_html(skin_name)

    assert isinstance(html, str)
    assert len(html) > 0
    # убрать assert "line1" in html

    safe_name = skin_name.replace(" ", "_").replace("|", "").replace("/", "")
    path = OUTPUTS_DIR / f"history_{safe_name}.html"
    path.write_text(html, encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════ #
#  fetch_inventory                                                    #
# ═══════════════════════════════════════════════════════════════════ #


def test_fetch_inventory(client, config):
    data = client.fetch_inventory(config.parser.steam_id)

    assert isinstance(data, dict)

    path = OUTPUTS_DIR / "inventory.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


# ═══════════════════════════════════════════════════════════════════ #
#  fetch_my_market_page                                               #
# ═══════════════════════════════════════════════════════════════════ #


def test_fetch_my_market_page(client):
    html = client.fetch_my_market_page()

    assert isinstance(html, str)
    assert len(html) > 0

    path = OUTPUTS_DIR / "my_market_page.html"
    path.write_text(html, encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════ #
#  fetch_my_history                                                   #
# ═══════════════════════════════════════════════════════════════════ #


@pytest.mark.parametrize("start,count", [(0, 10), (0, 50)])
def test_fetch_my_history(client, start, count):
    data = client.fetch_my_history(start=start, count=count)

    assert isinstance(data, dict)
    assert "results_html" in data
    assert "total_count" in data
    assert isinstance(data["total_count"], int)

    path = OUTPUTS_DIR / f"my_history_{start}_{count}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
