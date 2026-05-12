# Назначение:
# - Превращают грязные данные в пригодные.
# Имеют право:
# - удалять мусор
# - сортировать
# - агрегировать
# - дедуплицировать
# - нормализовывать
# НЕ имеют права:
# - принимать решения
# - считать сигналы
# - анализировать рынок
from collections import defaultdict
from datetime import datetime, timezone
import numpy as np
import logging
import core.objects as obj
from typing import List

log = logging.getLogger("analysis.cleaners")


def aggregate_daily(history: List[obj.ItemPriceHistory]) -> List[obj.ItemPriceHistory]:
    log = logging.getLogger("analysis.cleaners.aggregate_daily")
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
    log = logging.getLogger("analysis.filters.outliers_iqr")
    if not raw_history:
        log.error("remove_price_outliers_iqr called on empty raw_history")
        raise NotImplementedError

    monthly = defaultdict(list)
    for rec in raw_history:
        monthly[(rec.date.year, rec.date.month)].append(rec)

    cleaned = []
    cleaned_inc = 0

    for _, records in monthly.items():
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
        cleaned_inc += 1
        cleaned.extend(filtered)
    log.debug(f"cleaned: {cleaned_inc}")
    history = sorted(cleaned, key=lambda r: r.date)
    log.debug("History size after IQR cleaning: %d", len(history))
    return history


def extract_prices(history):
    return [h.price for h in history if h.price is not None]


def extract_year_prices(history, cutoff):
    return [h.price for h in history if h.price and h.date >= cutoff]


def sort_history(history):
    return sorted(history, key=lambda r: r.date) if history else []


def prepare_history(history, factor, q_arr):

    history = aggregate_daily(history)

    history = remove_price_outliers_iqr(
        history,
        factor,
        q_arr,
    )

    return history
