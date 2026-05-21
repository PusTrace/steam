# Strategy должна:
# только:
# - вызывать pipeline
# - комбинировать сигналы
# - принимать итоговое решение
# Strategy НЕ должна:
# - считать regression
# - фильтровать массивы
# - искать median
# - чистить данные

import logging
from datetime import datetime, timedelta, timezone
from typing import List

import core.models as obj
import analysis.cleaners as cleaners
import analysis.features as features
import analysis.filters as filters

log = logging.getLogger("strategy")


class BaseStrategy:
    def process(self, market_data: obj.ItemMarketData):
        raise NotImplementedError

    def decide(self, processed: obj.ItemProcessed, market_data: obj.ItemMarketData):
        raise NotImplementedError


class EVA(BaseStrategy):
    def __init__(self, plot):
        config = obj.load_config()
        cfg = config.analysis
        self.plot = plot
        self.cfg = cfg

    def decide(self, processed: obj.ItemProcessed, market_data: obj.ItemMarketData):
        raw_history = market_data.history
        buy_orders = market_data.buy_orders
        sell_orders = market_data.sell_orders

        if not raw_history:
            log.error("No raw_history provided")
            return None, None

        # === ФИЛЬТР 1: Проверка на памп/дамп ===
        if filters.is_market_pumped(
            raw_history,
            self.cfg.boost_threshold,
            self.cfg.volatility_threshold,
        ):
            return None

        # === АНАЛИЗ СТАКАНОВ ===
        result = self.check_order_book(market_data=market_data, processed=processed)

        if result is not None:
            price, amount = result
            log.info(f"✓ BUY DECISION: {price:.2f}₸ x{amount}")
            if processed.avg_week is not None:
                discount = (1 - price / processed.avg_week) * 100
                log.debug(f"Discount from avg_week: {discount:.1f}%")
            if processed.moment is not None:
                log.debug(
                    f"Price vs moment: {((price / processed.moment - 1) * 100):+.1f}%"
                )
        else:
            log.info("✗ SKIP")

        return result

    def process(
        self, market_data: obj.ItemMarketData
    ) -> tuple[obj.ItemProcessed, List[obj.ItemPriceHistory]] | None:
        raw_history = market_data.history
        buy_orders = market_data.buy_orders
        sell_orders = market_data.sell_orders

        high, low, volume, moment = features.bef_cleaning_summary(
            raw_history, self.cfg.approx_multiplier
        )

        clean_history = cleaners.prepare_history(
            raw_history,
            self.cfg.factor,
            self.cfg.q_arr,
        )

        history_features = features.build_history_features(clean_history)

        ob_metrics = features.orders_metrics(
            buy_orders=buy_orders, sell_orders=sell_orders
        )

        processed = obj.RawProcessed(
            weight=None,
            slope_6m=history_features.linreg_6m_data.slope,
            intercept_6m=history_features.linreg_6m_data.intercept,
            slope_1m=history_features.linreg_1m_data.slope,
            intercept_1m=history_features.linreg_1m_data.intercept,
            avg_month=history_features.avg_month,
            avg_week=history_features.avg_week,
            volume=volume,
            high=high,
            low=low,
            moment=moment,
            avg_5_sell_orders=ob_metrics.avg_5_sell_orders,
            avg_5_buy_orders=ob_metrics.avg_5_buy_orders,
            spread=ob_metrics.spread,
            mid_price=ob_metrics.mid_price,
            spread_percent=ob_metrics.spread_percent,
            bid_depth=ob_metrics.bid_depth,
        )

        processed = features.item_weight(processed)

        processed = filters.to_valid(processed)
        if processed is None:
            log.warning("Processed Validator return None")
            return None

        log.debug(f"weight: {processed.weight}")
        log.debug(f"processing_data: {processed}")

        return processed, clean_history

    def check_order_book(
        self, processed: obj.ItemProcessed, market_data: obj.ItemMarketData
    ) -> tuple[float, int] | None:

        threshold = features.calculate_threshold(
            processed.avg_week,
            sum(o.price for o in market_data.sell_orders[:5]) / 5,
            processed.slope_1m,
            self.cfg.down_trende_multiplier,
            self.cfg.up_trende_multiplier,
        )

        if threshold is None:
            log.warning("threshold is None")
            return None

        orders = filters.filter_by_threshold(market_data.buy_orders, threshold)

        if len(orders) < 1:
            log.warning("len of orders < 1")
            return None

        zone = filters.filter_price_zone(
            orders, threshold, self.cfg.price_zone_percentage
        )

        if not zone:
            log.warning("[ZONE] is not found")
            return None

        walls = features.find_liquidity_walls(zone)
        if not walls:
            log.warning("[WALLS] are not found")
            return None

        price = features.select_best_wall(walls, processed.avg_week)
        if processed.slope_1m is not None:
            amount = 2 if processed.slope_1m < 0 else 1
        else:
            amount = 1

        return round(price, 2), amount


class PTModel:
    """Обёртка для разных стратегий торговли"""

    def __init__(self, model_type: str, plot: bool = False):

        strategies = {"EVA": EVA}

        if model_type not in strategies:
            raise ValueError(f"Unknown model type: {model_type}")

        self.strategy = strategies[model_type](plot=plot)

    def decide(self, processed: obj.ItemProcessed, market_data: obj.ItemMarketData):
        return self.strategy.decide(processed=processed, market_data=market_data)

    def process(self, market_data: obj.ItemMarketData):
        return self.strategy.process(market_data=market_data)


def select_best_wall(walls, avg_week):
    best = max(walls, key=lambda x: x["price"])
    return best["price"] + avg_week * 0.001
