from . import orders
from . import sell
from . import buy
import requests


class TradeService:
    """
    Responsibilities:
        - create buy order
        - cancel buy order
        - sell skin
        - buy skin by listing id
    """

    def __init__(self, session: requests.Session):
        self.session = session

    def create_buy_order(self, name, price, qty, conf_id: int = 0):
        orders.create_buy_order(
            cookies=self.session.cookies,
            market_hash_name=name,
            price=price,
            quantity=qty,
            confirmation_id=conf_id,
        )

    def cancel_buy_order(self, name, buy_order_id):
        orders.cancel_order(
            skin=name, buy_order_id=buy_order_id, cookies=self.session.cookies
        )

    def sell_skin(self, price, asset_id):
        sell.sell_skin(price=price, asset_id=asset_id, cookies=self.session.cookies)

    def buy_skin_by_listing_id(self, listing_id, price, price_without_fee, sessionid):
        buy.buy_skin_by_listing_id(
            session=self.session,
            listing_id=listing_id,
            price=price,
            price_without_fee=price_without_fee,
            sessionid=sessionid,
        )
