from .market.client import SteamMarketClient
from .market.service import MarketService


class SteamAPI:
    def __init__(self, session, config):
        client = SteamMarketClient(session, config)
        self.market = MarketService(client)
