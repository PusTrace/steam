from collections import defaultdict
from datetime import datetime, timezone
import numpy as np
import logging
import core.objects as obj
from typing import List


def aggregate_daily(history: List[obj.ItemPriceHistory]) -> List[obj.ItemPriceHistory]:
    log = logging.getLogger("aggregate_daily")
    if not history:
        log.error("aggregate_daily: empty history")
        raise NotImplementedError

    daily = defaultdict(list)
    for item in history:
        dt = item.date
        price = item.price
        volume = item.volume
        daily[dt.date()].append((price, volume))

    aggregated = []
    for day, records in daily.items():
        prices = [p for p, _ in records if p is not None]
        volumes = [v for _, v in records]

        if not prices:
            log.debug("Skipping day %s: no valid prices", day)
            continue

        aggregated.append(
            obj.ItemPriceHistory(
                date=datetime(day.year, day.month, day.day, tzinfo=timezone.utc),
                price=sum(prices) / len(prices),
                volume=sum(volumes),
            )
        )

    history = sorted(aggregated, key=lambda r: r.date)
    log.debug("aggregate_daily result size: %d", len(history))
    return history


def remove_price_outliers_iqr(
    raw_history: List[obj.ItemPriceHistory], factor: float, q_arr: List
) -> List[obj.ItemPriceHistory]:
    log = logging.getLogger("outliers_iqr")
    if not raw_history:
        log.error("remove_price_outliers_iqr called on empty raw_history")
        raise NotImplementedError

    monthly = defaultdict(list)
    for rec in raw_history:
        monthly[(rec.date.year, rec.date.month)].append(rec)

    cleaned = []

    for key, records in monthly.items():
        prices = np.array([r.price for r in records if r.price is not None])

        if len(prices) < 4:
            cleaned.extend(records)
            continue

        q1, q3 = np.percentile(prices, q_arr)
        iqr = q3 - q1
        low, high = q1 - factor * iqr, q3 + factor * iqr

        filtered = [
            r for r in records if r.price is not None and low <= r.price <= high
        ]

        log.debug("[%s] IQR cleaned %d → %d", key, len(records), len(filtered))

        cleaned.extend(filtered)

    history = sorted(cleaned, key=lambda r: r.date)
    log.debug("History size after IQR cleaning: %d", len(history))
    return history
