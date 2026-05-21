import time
import random
import logging
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)


def _retry(func, max_retries: int, delay_range: tuple):
    """Generic retry wrapper for any callable that may raise RequestException."""
    for attempt in range(max_retries):
        try:
            return func()
        except requests.RequestException as e:
            if attempt == max_retries - 1:
                logger.error("Failed after %d attempts: %s", max_retries, e)
                raise
            delay = random.uniform(*delay_range)
            logger.warning(
                "Request failed (attempt %d/%d): %s. Retry in %.2fs",
                attempt + 1,
                max_retries,
                e,
                delay,
            )
            time.sleep(delay)


class SteamMarketClient:
    """Pure HTTP layer — no parsing, no business logic."""

    def __init__(self, session: requests.Session, config):
        self.session = session
        self.cfg = config.parser

    # ------------------------------------------------------------------ #
    #  Market data                                                         #
    # ------------------------------------------------------------------ #

    def fetch_orders(self, item_name_id: str) -> dict:
        url = "https://steamcommunity.com/market/itemordershistogram"
        params = {
            "country": self.cfg.country,
            "language": "english",
            "currency": self.cfg.currency,
            "item_nameid": item_name_id,
            "norender": 1,
        }

        def _req():
            r = self.session.get(url, params=params, timeout=30)
            r.raise_for_status()
            return r.json()

        return _retry(_req, self.cfg.max_retries, self.cfg.retry_delay_range)

    def fetch_price_history_html(self, name: str) -> str:
        encoded = quote(name, safe="")
        url = f"https://steamcommunity.com/market/listings/{self.cfg.appid}/{encoded}?currency={self.cfg.currency}"

        def _req():
            r = self.session.get(url, timeout=30)
            r.raise_for_status()
            return r.text

        return _retry(_req, self.cfg.max_retries, self.cfg.retry_delay_range)

    # ------------------------------------------------------------------ #
    #  Inventory                                                           #
    # ------------------------------------------------------------------ #

    def fetch_inventory(
        self, steam_id: int, appid: str = "730", context: str = "2"
    ) -> dict:
        url = f"https://steamcommunity.com/inventory/{steam_id}/{appid}/{context}"

        def _req():
            r = self.session.get(url, timeout=30)
            r.raise_for_status()
            return r.json()

        return _retry(_req, self.cfg.max_retries, self.cfg.retry_delay_range)

    # ------------------------------------------------------------------ #
    #  My market state (active listings / buy-orders / wallet)            #
    # ------------------------------------------------------------------ #

    def fetch_my_market_page(self) -> str:
        """Returns raw HTML of the personal market page."""

        def _req():
            r = self.session.get(
                "https://steamcommunity.com/market/",
                cookies={"ActListPageSize": "100"},
                timeout=15,
                allow_redirects=True,
            )
            r.raise_for_status()
            return r.text

        return _retry(_req, self.cfg.max_retries, self.cfg.retry_delay_range)

    # ------------------------------------------------------------------ #
    #  Transaction history                                                 #
    # ------------------------------------------------------------------ #

    def fetch_my_history(self, start: int = 0, count: int = 100) -> dict:
        url = (
            "https://steamcommunity.com/market/myhistory/render/"
            f"?query=&start={start}&count={count}"
        )

        def _req():
            r = self.session.get(url, timeout=15, allow_redirects=True)
            r.raise_for_status()
            return r.json()

        return _retry(_req, self.cfg.max_retries, self.cfg.retry_delay_range)
