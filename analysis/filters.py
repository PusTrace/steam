# Назначение
# проверка предмета
# Их задача:
# Решить:
# continue / reject
# Они используют:
# - features
# - cleaned data
# Они НЕ должны:
# - считать сложную математику
# - мутировать данные
# - orchestration

import logging
import core.objects as obj
import analysis.cleaners as cleaners
import analysis.features as features
from datetime import datetime, timedelta, timezone

log = logging.getLogger("analysis.filters")


def filter_by_threshold(buy_orders, threshold: float):
    return [o for o in buy_orders if o.price <= threshold]


def filter_price_zone(orders, threshold, percentage):
    min_price = orders[-1].price
    price_range = threshold - min_price
    min_realistic = threshold - (price_range * percentage)
    return [o for o in orders if o.price >= min_realistic]


def to_valid(processed: obj.RawProcessed) -> obj.ItemProcessed | None:
    for field_name in processed.__dataclass_fields__:
        if getattr(processed, field_name) is None:
            return None

    return obj.ItemProcessed(**processed.__dict__)


def is_market_pumped(history, boost_threshold, volatility_threshold):

    if len(history) < 20:
        return True

    prices = cleaners.extract_prices(history)

    if len(prices) < 20:
        return True

    cutoff = datetime.now(timezone.utc) - timedelta(days=365)

    year_prices = cleaners.extract_year_prices(history, cutoff)

    boost = features.price_boost(prices, year_prices)

    if boost >= boost_threshold:
        log.info(f"Boost {boost:.1f}%")
        return True

    vol = features.volatility(prices)

    if vol > volatility_threshold:
        log.info(f"Volatility too high: {vol:.1f}%")
        return True

    return False
