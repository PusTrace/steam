"""
Pure parsing functions — take raw bytes/dicts, return domain objects.
No network, no DB, no side-effects.
"""

from os import name
import re
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List

from bs4 import BeautifulSoup

from .models import (
    ItemPriceHistory,
    ItemOrder,
    UserInventory,
    UserBuyOrder,
    UserSellOrder,
    UserHistory,
)
from core.utils import normalize_date

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
#  Price history                                                       #
# ------------------------------------------------------------------ #


def fix_encoding(text: str) -> str:
    try:
        return text.encode("latin1").decode("utf-8")
    except UnicodeError:
        return text


def extract_price_history(html: str) -> dict[str, list]:
    match = re.search(
        r"window\.SSR\.renderContext\s*=\s*JSON\.parse\(\"([\s\S]*?)\"\);", html
    )
    if not match:
        raise ValueError("window.SSR.renderContext not found in HTML")
    raw = match.group(1).encode().decode("unicode_escape")
    context = json.loads(raw)
    query_data = json.loads(context["queryData"])

    result = {}

    for q in query_data["queries"]:
        key = q.get("queryKey", [])
        if len(key) == 4 and key[:3] == ["market", "pricehistory", 730]:
            skin_name = fix_encoding(key[3])
            result[skin_name] = q["state"]["data"]["prices"]

    if not result:
        raise ValueError("No pricehistory found in HTML")
    return result


def parse_price_history(
    raw_histories: dict[str, list],
) -> dict[str, list[ItemPriceHistory]]:
    result = {}
    for skin_name, entries in raw_histories.items():
        parsed = []
        for entry in entries:
            try:
                dt = datetime.fromtimestamp(entry["time"], tz=timezone.utc)
                dt = normalize_date(dt)
                price = float(entry["price_median"])
                volume = int(entry["purchases"])
                parsed.append(ItemPriceHistory(date=dt, price=price, volume=volume))
            except (ValueError, KeyError) as e:
                logger.error("Malformed price history entry %s: %s", entry, e)
        result[skin_name] = parsed
    return result


# ------------------------------------------------------------------ #
#  Orders                                                              #
# ------------------------------------------------------------------ #


def _parse_order_list(raw: list) -> list[ItemOrder]:
    return [ItemOrder(price=float(p), qty=int(q)) for p, q, *_ in raw]


def parse_orders(data: dict) -> tuple[list[ItemOrder], list[ItemOrder]]:
    buy = _parse_order_list(data.get("buy_order_graph", []))
    sell = _parse_order_list(data.get("sell_order_graph", []))
    return buy, sell


# ------------------------------------------------------------------ #
#  Inventory                                                           #
# ------------------------------------------------------------------ #


def parse_inventory(data: dict) -> list[UserInventory]:
    assets = data.get("assets", [])
    descriptions = data.get("descriptions", [])
    asset_properties = data.get("asset_properties", [])

    # asset_id → (float_value, int_value)
    properties_map: dict[str, tuple] = {}
    for prop in asset_properties:
        assetid = prop.get("assetid")
        float_value, int_value = None, None
        for p in prop.get("asset_properties", []):
            if "float_value" in p:
                float_value = float(p["float_value"])
            if "int_value" in p:
                int_value = int(p["int_value"])
        properties_map[assetid] = (float_value, int_value)

    # (classid, instanceid) → first matching assetid
    asset_lookup: dict[tuple, str] = {}
    for asset in assets:
        key = (asset.get("classid"), asset.get("instanceid"))
        if key not in asset_lookup:
            asset_lookup[key] = asset.get("assetid")

    result = []
    for item in descriptions:
        classid = item.get("classid")
        instanceid = item.get("instanceid")
        owner_descriptions = item.get("owner_descriptions")
        marketable_time = (
            owner_descriptions[1].get("value") if owner_descriptions else None
        )

        asset_id = asset_lookup.get((classid, instanceid), "0")
        float_value, int_value = properties_map.get(asset_id, (None, None))

        result.append(
            UserInventory(
                name=item.get("market_hash_name"),
                class_id=classid,
                instance_id=instanceid,
                asset_id=asset_id,
                marketable_time=marketable_time,
                float_value=float_value,
                int_value=int_value,
            )
        )
    return result


# ------------------------------------------------------------------ #
#  My market state                                                     #
# ------------------------------------------------------------------ #


def _clean_price(text: str) -> float | None:
    cleaned = text.replace("₸", "").replace(" ", "").replace(",", ".")
    match = re.search(r"\d+(\.\d+)?", cleaned)
    return float(match.group()) if match else None


def parse_my_market_page(
    html: str,
) -> tuple[float, float, list[UserBuyOrder], list[UserSellOrder]]:
    soup = BeautifulSoup(html, "html.parser")

    buy_orders: list[UserBuyOrder] = []
    sell_orders: list[UserSellOrder] = []
    total_buyorders = 0.0
    wallet_balance = 0.0

    # ── buy orders ──────────────────────────────────────────────────
    for row in soup.find_all("div", id=re.compile(r"^mybuyorder_\d+$")):
        full_id = row.get("id", "")
        parts = full_id.split("_")
        if len(parts) != 2 or not parts[1].isdigit():
            logger.warning("Bad buy-order id: %s", full_id)
            continue
        order_id = int(parts[1])

        name_tag = row.select_one(".market_listing_item_name_link")
        if not name_tag:
            continue
        skin_name = name_tag.get_text(strip=True)

        price_tags = row.select(".market_listing_my_price .market_listing_price")
        if not price_tags:
            continue
        price_text = price_tags[0].get_text(strip=True).split("@")[-1]
        price = _clean_price(price_text)
        if price is None:
            continue

        qty_tag = row.select_one(".market_listing_inline_buyorder_qty")
        qty = 1
        if qty_tag:
            m = re.search(r"\d+", qty_tag.get_text())
            qty = int(m.group()) if m else 1

        total_buyorders += price * qty
        buy_orders.append(
            UserBuyOrder(id=order_id, name=skin_name, price=price, qty=qty)
        )

    # ── sell orders ──────────────────────────────────────────────────
    for row in soup.find_all("div", id=re.compile(r"^mylisting_\d+$")):
        full_id = row.get("id", "")
        parts = full_id.split("_")
        if len(parts) != 2 or not parts[1].isdigit():
            logger.warning("Bad sell-order id: %s", full_id)
            continue
        order_id = int(parts[1])

        name_tag = row.select_one(".market_listing_item_name_link")
        if not name_tag:
            continue
        skin_name = name_tag.get_text(strip=True)

        date_tag = row.select_one(
            ".market_listing_right_cell.market_listing_listed_date.can_combine"
        )
        date_text = date_tag.get_text(strip=True) if date_tag else ""

        price_tag = row.select_one(".market_listing_right_cell.market_listing_my_price")
        if not price_tag:
            continue
        price_text = re.sub(r"\(.*?\)", "", price_tag.get_text(strip=True))
        price = _clean_price(price_text)
        if price is None:
            continue

        sell_orders.append(
            UserSellOrder(id=order_id, name=skin_name, date=date_text, price=price)
        )

    # ── wallet ───────────────────────────────────────────────────────
    wallet_tag = soup.select_one(".responsive_menu_user_wallet a")
    if wallet_tag:
        m = re.search(r"([\d\s]+[,\.]\d+)", wallet_tag.get_text(strip=True))
        if m:
            wallet_balance = float(m.group(1).replace(" ", "").replace(",", "."))

    return total_buyorders, wallet_balance, buy_orders, sell_orders


# ------------------------------------------------------------------ #
#  Transaction history                                                 #
# ------------------------------------------------------------------ #


def parse_my_history(data: dict) -> tuple[list[UserHistory], int]:
    results_html = data.get("results_html", "")
    assets = data.get("assets", {}).get("730", {}).get("2", {})
    total_count = data.get("total_count", 0)

    soup = BeautifulSoup(results_html, "html.parser")
    items: list[UserHistory] = []

    for row in soup.select(".market_listing_row"):
        img_elem = row.select_one("img[id$='_image']")
        if not img_elem:
            continue

        # match asset by icon_url fragment
        assetid = None
        for key, asset_val in assets.items():
            icon = asset_val.get("icon_url", "")
            if icon and icon.split("/")[-1] in img_elem["src"]:
                assetid = key
                break
        if not assetid or assetid not in assets:
            continue

        market_name = assets[assetid].get("market_hash_name")

        price_elem = row.select_one(".market_listing_their_price .market_listing_price")
        date_elems = row.select(".market_listing_listed_date.can_combine")
        gain_loss_elem = row.select_one(
            ".market_listing_left_cell.market_listing_gainorloss"
        )

        price = None
        if price_elem:
            raw = price_elem.text.strip().split("(")[0]
            raw = raw.replace("₸", "").replace(",", ".").replace(" ", "")
            try:
                price = float(raw)
            except ValueError:
                pass

        gain_loss = bool(gain_loss_elem and gain_loss_elem.text.strip() == "+")
        acted_on = date_elems[0].text.strip() if len(date_elems) > 0 else None
        listed_on = date_elems[1].text.strip() if len(date_elems) > 1 else None

        if price is None or acted_on is None or listed_on is None:
            logger.error(
                "Incomplete history row — price=%s acted_on=%s listed_on=%s",
                price,
                acted_on,
                listed_on,
            )
            continue

        items.append(
            UserHistory(
                asset_id=assetid,
                name=market_name,
                price=price,
                acted_on=acted_on,
                listed_on=listed_on,
                gain_loss=gain_loss,
            )
        )

    return items, total_count
