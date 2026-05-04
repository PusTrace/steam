# analysis/strategies.py

import logging
from typing import List

import core.objects as obj
import analysis.cleaners as cleaners
import analysis.features as features
import analysis.filters as filters
import analysis.plot as plot

log = logging.getLogger("strategy")


class BaseStrategy:
    def process(self, market_data: obj.ItemMarketData):
        raise NotImplementedError

    def decide(
        self,
        processed: obj.ItemProcessed,
        market_data: obj.ItemMarketData,
        clean_history: List[obj.ItemPriceHistory],
    ):
        raise NotImplementedError


class EVA(BaseStrategy):

    def __init__(self):
        config = obj.load_config()
        cfg = config.analysis
        self.order_book_analyzer = filters.OrderBookAnalyzer(cfg=cfg)
        self.pump_detector = filters.PumpDetector(cfg=cfg)
        self.plot = False
        self.cfg = cfg

    def decide(
        self,
        processed: obj.ItemProcessed,
        market_data: obj.ItemMarketData,
        clean_history: List[obj.ItemPriceHistory],
    ):
        raw_history = market_data.history
        buy_orders = market_data.buy_orders
        sell_orders = market_data.sell_orders

        if not raw_history:
            log.error("No raw_history provided")
            return None, None

        # === ФИЛЬТР 1: Проверка на памп/дамп ===
        pump_indicator = self.pump_detector.check(
            history=clean_history,
        )

        if pump_indicator:
            return None, None

        # === ФИЛЬТР 2: Предварительные проверки ===
        if len(buy_orders) <= 0:
            log.error("No buy orders available, skipping")
            return None, None

        if len(sell_orders) <= 0:
            log.error("No sell orders available, skipping")
            return None, None

        log.debug(
            f"Market depth: {len(buy_orders)} buy orders, {len(sell_orders)} sell orders"
        )

        # === АНАЛИЗ СТАКАНОВ ===
        price, amount = self.order_book_analyzer.analyze(
            buy_orders=buy_orders, sell_orders=sell_orders, processed=processed
        )

        if price is not None:
            log.info(f"✓ BUY DECISION: {price:.2f}₸ x{amount}")
            if processed.avg_week is not None:
                discount = (1 - price / processed.avg_week) * 100
                log.debug(f"Discount from avg_week: {discount:.1f}%")
            if processed.moment is not None:
                log.debug(
                    f"Price vs moment: {((price / processed.moment - 1) * 100):+.1f}%"
                )
        else:
            log.info("✗ SKIP: no suitable price found")

        return price, amount

    def process(self, market_data: obj.ItemMarketData):
        raw_history = market_data.history
        buy_orders = market_data.buy_orders
        sell_orders = market_data.sell_orders

        high, low, volume, moment = features.bef_cleaning_summary(
            raw_history, self.cfg.approx_multiplier
        )

        raw_history = cleaners.aggregate_daily(raw_history)

        clean_history = cleaners.remove_price_outliers_iqr(
            raw_history, self.cfg.factor, self.cfg.q_arr
        )

        analyzer = features.HistoryAnalyzer(clean_history)

        slope_6m, _, _, _ = analyzer.linreg(analyzer.six_month_ago)
        slope_1m, _, _, _ = analyzer.linreg(analyzer.one_month_ago)

        avg_month = analyzer.calc_avg(analyzer.one_month_ago)
        avg_week = analyzer.calc_avg(analyzer.one_week_ago)

        if self.plot:
            plot.plot_analysis(raw_history, clean_history, slope_6m, slope_1m)

        avg_5_sell_orders = sum(o.price for o in sell_orders[:5]) / 5
        avg_5_buy_orders = sum(o.price for o in buy_orders[:5]) / 5
        if buy_orders:
            bid_depth = buy_orders[min(4, len(buy_orders) - 1)].qty
            bid_depth = int(bid_depth)
        else:
            bid_depth = None  # или любое значение по умолчанию

        spread = avg_5_sell_orders - avg_5_buy_orders
        mid_price = (avg_5_sell_orders + avg_5_buy_orders) / 2

        spread_percent = spread / mid_price  # например 0.05 = 5%

        processed = obj.ItemProcessed(
            slope_6m=slope_6m,
            slope_1m=slope_1m,
            avg_month=avg_month,
            avg_week=avg_week,
            volume=volume,
            high=high,
            low=low,
            moment=moment,
            avg_5_sell_orders=avg_5_sell_orders,
            avg_5_buy_orders=avg_5_buy_orders,
            spread=spread,
            mid_price=mid_price,
            spread_percent=spread_percent,
            bid_depth=bid_depth,
        )
        log.debug(f"processing_data: {processed}")
        # analysis_id = self.db.update_skins_analysis(skin.id, data)
        # self.db.commit()

        return processed, clean_history


class PTModel:
    """Обёртка для разных стратегий торговли"""

    def __init__(self, model_type: str):

        strategies = {"EVA": EVA}

        if model_type not in strategies:
            raise ValueError(f"Unknown model type: {model_type}")

        self.strategy = strategies[model_type]()

    def decide(self, market_data: obj.ItemMarketData):
        processed, clean_history = self.strategy.process(market_data)
        return self.strategy.decide(
            processed=processed, market_data=market_data, clean_history=clean_history
        )

    def process(self, market_data: obj.ItemMarketData):
        return self.strategy.process(market_data=market_data)
