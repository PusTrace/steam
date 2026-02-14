import logging
from datetime import datetime, timedelta, timezone
import numpy as np

def bef_cleaning_summary(raw_history):
    log = logging.getLogger("bef_cleaning_history")
    now = datetime.now(tz=timezone.utc)
    one_week_ago = now -timedelta(7)
    one_month_ago = now -timedelta(30)
    
    moment_price = raw_history[-1][1] if raw_history else None
    log.debug("Moment price: %s", moment_price)
    
    month_prices = []
    week_volumes = []

    for dt, price, volume in raw_history:
        if dt >= one_week_ago:
            week_volumes.append(volume)
        if dt >= one_month_ago and price is not None:
            month_prices.append(price)

    volume = sum(week_volumes) if week_volumes else None

    if not month_prices:
        log.warning("No month prices available for high/low approx")

    sorted_month = sorted(month_prices)
    high_approx = sum(sorted_month[-3:]) / min(3, len(sorted_month)) if sorted_month else None
    low_approx = sum(sorted_month[:3]) / min(3, len(sorted_month)) if sorted_month else None

    log.debug(
        "bef_cleaning_summary: volume=%s high=%s low=%s moment=%s",
        volume, high_approx, low_approx, moment_price
    )

    return high_approx, low_approx, volume, moment_price




class HistoryAnalyzer:
    def __init__(self, history):
        self.logger = logging.getLogger(__name__)

        self.logger.debug("Initializing HistoryAnalyzer")
        self.logger.debug("Raw history length: %d", len(history))

        self.history = sorted(history, key=lambda r: r[0]) if history else []

        if not self.history:
            self.logger.error("Empty history passed to HistoryAnalyzer")

        self.now = datetime.now(timezone.utc)
        self.one_week_ago = self.now - timedelta(days=7)
        self.one_month_ago = self.now - timedelta(days=30)
        self.six_month_ago = self.now - timedelta(days=180)

    def calc_avg(self, since_dt):
        since_dt_prices = []

        for dt, price, _ in self.history:
            if price is None:
                self.logger.debug("Skipping None price at %s", dt)
                continue

            if dt >= since_dt:
                since_dt_prices.append(price)

        len_since_dt_prices = len(since_dt_prices)
        if len_since_dt_prices > 0:
            avg = sum(since_dt_prices) / len_since_dt_prices if since_dt else None
        else:
            avg = None

        self.logger.debug(
            "calc_avg since %s: len_prices=%d avg=%s",
            since_dt, len_since_dt_prices, avg
        )

        return avg

    def linreg(self, since_dt):
        filtered = [(d, p) for d, p, _ in self.history if d >= since_dt and p is not None]

        if len(filtered) < 2:
            self.logger.debug("linreg skipped: not enough data since %s", since_dt)
            return None, None, None, None

        start = filtered[0][0]
        x = np.array([(d - start).total_seconds() / 86400 for d, _ in filtered])
        y = np.array([p for _, p in filtered])

        slope, intercept = np.polyfit(x, y, 1)
        self.logger.debug(
            "linreg result since %s: slope=%f intercept=%f",
            since_dt, slope, intercept
        )
        return float(slope), intercept, x, y

