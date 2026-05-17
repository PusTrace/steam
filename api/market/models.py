# dataclasses
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from core.objects import Skin


class ItemPriceHistory(BaseModel):
    date: datetime
    price: float
    volume: int


@dataclass
class ItemOrder:
    price: float
    qty: int


@dataclass
class ItemMarketData:
    history: list[ItemPriceHistory]
    buy_orders: list[ItemOrder]
    sell_orders: list[ItemOrder]
    skin: Skin


@dataclass
class UserHistory:
    name: str
    price: float
    asset_id: int
    acted_on: str
    listed_on: str
    gain_loss: bool


@dataclass
class UserBuyOrder:
    id: int
    name: str
    price: float
    qty: int


@dataclass
class UserSellOrder:
    id: int
    name: str
    price: float
    date: str


class UserInventory(BaseModel):
    name: str
    class_id: int
    instance_id: int
    asset_id: int
    marketable_time: Optional[str]
    float_value: Optional[float]
    int_value: Optional[int]
