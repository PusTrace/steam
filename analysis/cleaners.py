from collections import defaultdict
from datetime import datetime, timezone
import numpy as np
import logging



def aggregate_daily(history):
    log = logging.getLogger("aggregate_daily")
    if not history:
        log.warning("aggregate_daily: empty history")
        return

    daily = defaultdict(list)
    for dt, price, volume in history:
        daily[dt.date()].append((price, volume))

    aggregated = []
    for day, records in daily.items():
        prices = [p for p, _ in records if p is not None]
        volumes = [v for _, v in records]

        if not prices:
            log.debug("Skipping day %s: no valid prices", day)
            continue

        aggregated.append([
            datetime(day.year, day.month, day.day, tzinfo=timezone.utc),
            sum(prices) / len(prices),
            sum(volumes)
        ])

    history = sorted(aggregated, key=lambda r: r[0])
    log.debug("aggregate_daily result size: %d", len(history))
    return history




def remove_price_outliers_iqr(raw_history, factor: float = 0.2):
    log = logging.getLogger("outliers_iqr")
    if not raw_history:
        log.warning("remove_price_outliers_iqr called on empty raw_history")
        return

    monthly = defaultdict(list)
    for rec in raw_history:
        monthly[(rec[0].year, rec[0].month)].append(rec)

    cleaned = []

    for key, records in monthly.items():
        prices = np.array([r[1] for r in records if r[1] is not None])

        if len(prices) < 4:
            cleaned.extend(records)
            continue

        q1, q3 = np.percentile(prices, [25, 75])
        iqr = q3 - q1
        low, high = q1 - factor * iqr, q3 + factor * iqr

        filtered = [r for r in records if r[1] is not None and low <= r[1] <= high]


        log.debug(
            "[%s] IQR cleaned %d → %d",
            key, len(records), len(filtered)
        )

        cleaned.extend(filtered)

    history = sorted(cleaned, key=lambda r: r[0])
    log.debug("History size after IQR cleaning: %d", len(history))
    return history