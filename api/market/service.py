"""
MarketService — orchestration layer.
Knows about cache expiry, calls client for raw data, calls parser for objects.
"""

from .client import SteamMarketClient
from . import parser
from .models import (
    ItemMarketData,
    UserInventory,
    UserBuyOrder,
    UserSellOrder,
    UserHistory,
)


class MarketService:
    def __init__(self, client: SteamMarketClient):
        self.client = client

    # ------------------------------------------------------------------ #
    #  Market data                                                         #
    # ------------------------------------------------------------------ #

    def get_market_data(self, skin) -> ItemMarketData:
        buy_orders, sell_orders = self._get_orders(skin)
        history = self._get_price_history(skin)
        return ItemMarketData(
            history=history,
            buy_orders=buy_orders,
            sell_orders=sell_orders,
            skin=skin,
        )

    def _get_orders(self, skin):
        raw = self.client.fetch_orders(skin.item_name_id)
        buy, sell = parser.parse_orders(raw)
        return buy, sell

    def _get_price_history(self, skin):
        html = self.client.fetch_price_history_html(skin.name)
        raw = parser.extract_price_history(html, skin.name)
        return parser.parse_price_history(raw)

    # ------------------------------------------------------------------ #
    #  Inventory                                                           #
    # ------------------------------------------------------------------ #

    def get_inventory(self, steam_id: str) -> list[UserInventory]:
        raw = self.client.fetch_inventory(steam_id)
        return parser.parse_inventory(raw)

    # ------------------------------------------------------------------ #
    #  My market state                                                     #
    # ------------------------------------------------------------------ #

    def get_my_state(
        self,
    ) -> tuple[float, float, list[UserBuyOrder], list[UserSellOrder]]:
        html = self.client.fetch_my_market_page()
        return parser.parse_my_market_page(html)

    # ------------------------------------------------------------------ #
    #  Transaction history                                                 #
    # ------------------------------------------------------------------ #

    def get_my_history(
        self, start: int = 0, count: int = 100
    ) -> tuple[list[UserHistory], int]:
        raw = self.client.fetch_my_history(start, count)
        return parser.parse_my_history(raw)
