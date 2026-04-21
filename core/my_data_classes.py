from dataclasses import dataclass
from typing import List
import yaml


@dataclass
class PlaceOrdersConfig:
    user_want: List[str]
    deapth_of_thrirst: int


@dataclass
class Config:
    place_orders: PlaceOrdersConfig


def load_config(path: str) -> Config:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if "place_orders" not in raw:
        raise ValueError("Missing 'place_orders' section")

    po = raw["place_orders"]

    # базовая валидация
    user_want = po.get("user_want")
    depth = po.get("deapth_of_thirst")

    if not isinstance(user_want, list):
        raise TypeError("user_want must be a list")

    if not isinstance(depth, int):
        raise TypeError("deapth_of_thrirst must be an int")

    place_orders = PlaceOrdersConfig(
        user_want=user_want,
        deapth_of_thrirst=depth
    )

    return Config(place_orders=place_orders)
