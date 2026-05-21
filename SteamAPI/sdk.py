from .market.client import SteamMarketClient
from .market.service import MarketService
from .auth.service import AuthService
from .confirmation.service import ConfirmationService
from .trade.service import TradeService
from core.models import Secrets, Config


class SteamAPI:
    def __init__(self, secrets: Secrets, config: Config):
        # auth
        self.auth = AuthService(secrets)
        session = self.auth.login()
        # market
        client = SteamMarketClient(session=session, config=config)
        self.market = MarketService(client=client, secrets=secrets)
        # confirmation
        self.conf = ConfirmationService(session=session, mafile=secrets)
        # trade
        self.trade = TradeService(session=session)
