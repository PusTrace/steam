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
    down_trende_multiplier: float
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
    appid: int
    orders_cache_days: int
    prices_cache_days: int
    analysis_cache_days: int
    max_retries: int
    retry_delay_range: List[int]
    currency: int
    country: str
    steam_id: int


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


# ============== ITEM ============


class Skin(BaseModel):
    id: int
    name: str
    item_name_id: int
    orders_timestamp: Optional[datetime] = None
    history_timestamp: Optional[datetime] = None
    buy_price: Optional[float] = None


@dataclass
class ItemProcessed:
    weight: float
    slope_6m: float
    intercept_6m: float
    slope_1m: float
    intercept_1m: float
    avg_month: float
    avg_week: float
    volume: int
    high: float
    low: float
    moment: float
    avg_5_sell_orders: float
    avg_5_buy_orders: float
    spread: float
    mid_price: float
    spread_percent: float
    bid_depth: int


@dataclass
class RawProcessed:
    weight: Optional[float]
    slope_6m: float | None
    intercept_6m: float | None
    slope_1m: float | None
    intercept_1m: float | None
    avg_month: Optional[float]
    avg_week: Optional[float]
    volume: int | None
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
class ItemLinreg:
    slope: float | None
    intercept: float | None


@dataclass
class ItemHistoryFeatures:
    linreg_6m_data: ItemLinreg
    linreg_1m_data: ItemLinreg
    avg_month: float | None
    avg_week: float | None


@dataclass
class ItemOrdersFeatures:
    avg_5_sell_orders: float
    avg_5_buy_orders: float
    spread: float
    mid_price: float
    spread_percent: float
    bid_depth: int


@dataclass
class ItemDecision:
    name: str
    price: float
    amount: int
    score: float


def load_config() -> Config:
    with open("config/config.yaml", "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    return Config.model_validate(raw)
