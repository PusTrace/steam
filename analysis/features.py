# Назначение:
# Считать факты о данных.
# Это очень важно.
# Feature НЕ должен говорить:
# “покупать”
# Он должен говорить:
# “slope = -0.42”
# Имеют право:
# - математика
# - статистика
# - regression
# - volatility
# - averages
# - liquidity walls
# - spread
# НЕ имеют права:
# - skip
# - reject
# - buy
# - sell
# - decision making
import logging
from datetime import datetime, timedelta, timezone
import numpy as np
import core.models as obj
from typing import List
import analysis.cleaners as cleaners

log = logging.getLogger("analysis.features")


def avg_top_n(orders, n=5):
    if not orders:
        return None
    subset = orders[: min(n, len(orders))]
    return sum(o.price for o in subset) / len(subset)


def bef_cleaning_summary(raw_history: List[obj.ItemPriceHistory], approx_multiplier):
    now = datetime.now(tz=timezone.utc)
    one_week_ago = now - timedelta(7)
    one_month_ago = now - timedelta(30)

    moment_price = raw_history[-1].price if raw_history else None
    log.debug("Moment price: %s", moment_price)

    month_prices = []
    week_volumes = []

    for item in raw_history:
        dt = item.date
        price = item.price
        volume = item.volume

        if dt.tzinfo is None:
            log.warning("timezone is None replace with utc")
            dt = dt.replace(tzinfo=timezone.utc)

        if dt >= one_week_ago:
            week_volumes.append(volume)
        if dt >= one_month_ago and price is not None:
            month_prices.append(price)

    volume = sum(week_volumes) if week_volumes else 0

    if not month_prices:
        log.warning("No month prices available for high/low approx")

    sorted_month = sorted(month_prices)
    high_approx = (
        sum(sorted_month[-approx_multiplier:])
        / min(approx_multiplier, len(sorted_month))
        if sorted_month
        else None
    )
    low_approx = (
        sum(sorted_month[:approx_multiplier])
        / min(approx_multiplier, len(sorted_month))
        if sorted_month
        else None
    )

    log.debug(
        "bef_cleaning_summary: volume=%s high=%s low=%s moment=%s",
        volume,
        high_approx,
        low_approx,
        moment_price,
    )

    return high_approx, low_approx, volume, moment_price


def item_weight(
    processed: obj.RawProcessed,
) -> obj.RawProcessed:  # TODO: normalize items and calc normal weight
    weights = {
        "slope_6m": 2.0,
        "slope_1m": 1.5,
        "volume": 1,
        "spread": -1.5,  # большой спред = плохо
        "spread_percent": -2.0,  # тоже штраф
    }

    total_score = 0.0
    total_weight = 0.0

    for field, w in weights.items():
        value = getattr(processed, field)

        if value is None:
            continue

        total_score += value * w
        total_weight += abs(w)

    if total_weight > 0:
        processed.weight = total_score / total_weight
    else:
        processed.weight = None

    return processed


def calculate_threshold(avg_week, avg_sell, slope_1m, down_mult, up_mult):
    base = min(v for v in (avg_week, avg_sell) if v is not None)
    multiplier = down_mult if slope_1m < 0 else up_mult
    return base * multiplier


def find_liquidity_walls(orders):
    walls = []

    for i in range(len(orders) - 1):
        jump = orders[i + 1].qty - orders[i].qty
        if jump < 0:
            return None

        walls.append({"price": orders[i].price, "jump": jump, "score": jump})

    return sorted(walls, key=lambda x: x["score"], reverse=True)


def median(arr):
    arr = sorted(arr)
    n = len(arr)
    mid = n // 2

    return (arr[mid - 1] + arr[mid] / 2) if n % 2 == 0 else arr[mid]


def volatility(prices):
    if len(prices) < 2:
        return 0

    total = 0
    for i in range(1, len(prices)):
        if prices[i - 1] != 0:
            total += abs((prices[i] - prices[i - 1]) / prices[i - 1]) * 100

    return total / (len(prices) - 1)


def price_boost(prices, year_prices):
    if len(prices) < 50:
        return 0

    recent = prices[-50:]

    base = median(year_prices)
    current = median(recent)

    return ((current - base) / base) * 100


def get_time_windows():
    now = datetime.now(timezone.utc)
    return {
        "now": now,
        "week": now - timedelta(days=7),
        "month": now - timedelta(days=30),
        "six_month": now - timedelta(days=180),
    }


def calc_avg(history, since_dt):
    prices = [
        item.price
        for item in history
        if item.price is not None and item.date >= since_dt
    ]

    return sum(prices) / len(prices) if prices else None


def linreg(history, since_dt):
    filtered = [
        (item.date, item.price)
        for item in history
        if item.date >= since_dt and item.price is not None
    ]

    if len(filtered) < 2:
        return obj.ItemLinreg(slope=None, intercept=None)

    start = filtered[0][0]

    x = np.array([(d - start).total_seconds() / 86400 for d, _ in filtered])
    y = np.array([p for _, p in filtered])

    slope, intercept = np.polyfit(x, y, 1)

    return obj.ItemLinreg(slope=float(slope), intercept=float(intercept))


def build_history_features(history):

    history = cleaners.sort_history(history)

    windows = get_time_windows()

    return obj.ItemHistoryFeatures(
        linreg_6m_data=linreg(history, windows["six_month"]),
        linreg_1m_data=linreg(history, windows["month"]),
        avg_month=calc_avg(history, windows["month"]),
        avg_week=calc_avg(history, windows["week"]),
    )


def orders_metrics(buy_orders, sell_orders) -> obj.ItemOrdersFeatures:
    avg_5_sell_orders = sum(o.price for o in sell_orders[:5]) / 5
    avg_5_buy_orders = sum(o.price for o in buy_orders[:5]) / 5

    bid_depth = buy_orders[min(4, len(buy_orders) - 1)].qty
    bid_depth = int(bid_depth)

    spread = avg_5_sell_orders - avg_5_buy_orders
    mid_price = (avg_5_sell_orders + avg_5_buy_orders) / 2

    spread_percent = spread / mid_price  # например 0.05 = 5%

    return obj.ItemOrdersFeatures(
        avg_5_sell_orders=avg_5_buy_orders,
        avg_5_buy_orders=avg_5_sell_orders,
        spread=spread,
        mid_price=mid_price,
        spread_percent=spread_percent,
        bid_depth=bid_depth,
    )
