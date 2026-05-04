from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
import yaml


# =============== CONFIG ===========
class AnalysisConfig(BaseModel):
    approx_multiplier: int
    factor: float
    q_arr: List[int]
    down_trende_muliplier: float
    up_trende_multiplier: float
    volume_limit_multiplier: float
    price_zone_percentage: float
    min_walls: int
    max_walls: int
    boost_threshold: int
    volatility_threshold: int


class PlaceOrdersConfig(BaseModel):
    user_want: List[str]
    deapth_of_thirst: int


class ParserConfig(BaseModel):
    steam_appid: int
    orders_cache_days: int
    prices_cache_days: int
    analysis_cache_days: int
    max_retries: int
    retry_delay_range: List[int]
    currency: int
    country: str


class SellSkins(BaseModel):
    min_float_value: float
    steam_fee: float
    min_margin_percent: int
    dont_touch: List[str]
    over_price: List[str]
    op_multiplier: float


class Config(BaseModel):
    place_orders: PlaceOrdersConfig
    parser: ParserConfig
    sell_skins: SellSkins
    analysis: AnalysisConfig


# =========== USER ==============
@dataclass
class UserHistory:
    name: str
    price: float
    asset_id: int
    acted_on: str
    listed_on: str
    gain_loss: bool


@dataclass
class UserBuyOrders:
    id: int
    name: str
    price: float
    qty: int


@dataclass
class UserSellOrders:
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


# ============== ITEM ============
class Skin(BaseModel):
    id: int
    name: str
    item_name_id: int
    orders_timestamp: Optional[datetime] = None
    history_timestamp: Optional[datetime] = None
    buy_price: Optional[float] = None


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


class ItemProcessed(BaseModel):
    slope_6m: Optional[float]
    slope_1m: Optional[float]
    avg_month: Optional[float]
    avg_week: Optional[float]
    volume: Optional[int]
    high: Optional[float]
    low: Optional[float]
    moment: Optional[float]
    avg_5_sell_orders: Optional[float]
    avg_5_buy_orders: Optional[float]
    spread: Optional[float]
    mid_price: Optional[float]
    spread_percent: Optional[float]
    bid_depth: Optional[int]


@dataclass
class ItemDecision:
    name: str
    price: float
    amount: int
    score: float


def parse_orders(raw: list[list]) -> list[ItemOrder]:
    return [ItemOrder(price=p, qty=q) for p, q, _ in raw]


def load_config() -> Config:
    with open("config/config.yaml", "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    return Config.model_validate(raw)
