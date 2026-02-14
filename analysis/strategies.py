# analysis/strategies.py

import logging
from typing import Optional, Tuple

from analysis.cleaners import aggregate_daily, remove_price_outliers_iqr
from analysis.features import HistoryAnalyzer, bef_cleaning_summary
from analysis.filters import OrderBookAnalyzer, PumpDetector
from analysis.plot import plot_analysis

log = logging.getLogger("strategy")


class BaseStrategy:
    def decide(self, **kwargs):
        raise NotImplementedError
    

class EVA(BaseStrategy):
    
    def __init__(self, db):
        self.order_book_analyzer = OrderBookAnalyzer()
        self.pump_detector = PumpDetector()
        self.plot = False
        self.db = db
            

    def decide(self, **kwargs) -> Tuple[Optional[float], Optional[int]]:
        """
        EVA strategy: принимает историю и ордера, сам всё обрабатывает.
        
        Args:
            history: List[(datetime, price, volume)] — сырая история цен
            skin_orders: List[(price, volume)] — buy orders
            sell_orders: List[(price, volume)] — sell orders
        
        Returns:
            (price, amount) или (None, None)
        """
        raw_history = kwargs.get("history")
        buy_orders = kwargs.get('buy_orders')
        sell_orders = kwargs.get('sell_orders')
        skin_info = kwargs.get('skin_info')
        
        if not raw_history:
            log.error("No raw_history provided")
            return None, None
        
        log.debug("start processing")
        processing_data, history, analysis_id = self.processing(history=raw_history,
                                                   buy_orders=buy_orders,
                                                   sell_orders=sell_orders,
                                                   skin_info=skin_info)
        slope_6m, slope_1m, avg_month, avg_week, volume, high, low, moment, avg_5_sell_orders, avg_5_buy_orders, spread, mid_price, spread_percent, bid_depth = processing_data

        
        
        # === ФИЛЬТР 1: Проверка на памп/дамп ===
        pump_indicator = self.pump_detector.check(
            history=history,
        )
        
        if pump_indicator:
            return None, None

        
        # === ФИЛЬТР 2: Предварительные проверки ===
        if len(self.skin_orders) <= 0:
            log.error("No buy orders available, skipping")
            return None, None
        
        if len(self.sell_orders) <= 0:
            log.error("No sell orders available, skipping")
            return None, None
        
        log.debug(f"Market depth: {len(self.skin_orders)} buy orders, {len(self.sell_orders)} sell orders")
        
        # === АНАЛИЗ СТАКАНОВ ===
        y, amount = self.order_book_analyzer.analyze(
            buy_orders=buy_orders,
            sell_orders=sell_orders,
            avg_week_price=avg_week,
            slope_1m=slope_1m,
            volume_week=volume
        )

        
        if y is not None:
            log.info(f"✓ BUY DECISION: {y:.2f}₸ x{amount}")
            discount = (1 - y / self.avg_week_price) * 100
            log.debug(f"Discount from avg_week: {discount:.1f}%")
            log.debug(f"Price vs moment: {((y / self.moment_price - 1) * 100):+.1f}%")
        else:
            log.info("✗ SKIP: no suitable price found")
        
        
        return y, amount, analysis_id
    
    def processing(self, **kwargs):
        raw_history = kwargs.get('history')
        buy_orders = kwargs.get('buy_orders')
        sell_orders = kwargs.get('sell_orders')
        skin_info = kwargs.get('skin')
        
        high, low, volume, moment = bef_cleaning_summary(raw_history)
    
        raw_history = aggregate_daily(raw_history)
        
        history = remove_price_outliers_iqr(raw_history, 0.2)
        
        analyzer = HistoryAnalyzer(history)

        slope_6m, _, _, _= analyzer.linreg(analyzer.six_month_ago)
        slope_1m, _, _, _= analyzer.linreg(analyzer.one_month_ago)

        avg_month = analyzer.calc_avg(analyzer.one_month_ago)
        avg_week = analyzer.calc_avg(analyzer.one_week_ago)
        
        if self.plot:
            plot_analysis(raw_history, history, slope_6m, slope_1m)
            
        avg_5_sell_orders = sum(o[0] for o in sell_orders[:5]) / 5
        avg_5_buy_orders  = sum(o[0] for o in buy_orders[:5]) / 5
        if buy_orders:
            bid_depth = buy_orders[min(4, len(buy_orders)-1)][1]
            bid_depth = int(bid_depth)
        else:
            bid_depth = None  # или любое значение по умолчанию

        spread = avg_5_sell_orders - avg_5_buy_orders
        mid_price = (avg_5_sell_orders + avg_5_buy_orders) / 2

        spread_percent = spread / mid_price  # например 0.05 = 5%
        
        def f (value):
            if value is not None:
                return round(value, 2)
            else:
                return None
            
        data = (f(slope_6m), f(slope_1m), f(avg_month), f(avg_week), volume, f(high), f(low), f(moment), f(avg_5_sell_orders), f(avg_5_buy_orders), f(spread), f(mid_price), f(spread_percent), bid_depth)
        log.debug(f"processing_data: {data}")
        analysis_id = self.db.update_skins_analysis(skin_info[0], data)
        self.db.commit()
        return data, history, analysis_id
    


class PTModel:
    """Обёртка для разных стратегий торговли"""
    
    def __init__(self, model_type: str, db):
        
        strategies = {
            "EVA": EVA
        }

        if model_type not in strategies:
            raise ValueError(f"Unknown model type: {model_type}")

        self.strategy = strategies[model_type](db)

    def decide(self, **kwargs) -> Tuple[Optional[float], Optional[int]]:
        """
        Вычисляет фичи для предмета и принимает решение о покупке.
        
        Args:
            history: List[(datetime, price, volume)] — сырая история
            skin_orders: List[(price, volume)] — buy orders  
            sell_orders: List[(price, volume)] — sell orders
        
        Returns:
            (price, amount) или (None, None)
        """
        return self.strategy.decide(**kwargs)
    
    def processing(self, **kwargs):
        """
        Вычисляет фичи для предмета
        
        Args:
            history: List[(datetime, price, volume)] — сырая история
            skin_orders: List[(price, volume)] — buy orders  
            sell_orders: List[(price, volume)] — sell orders
        
        Returns: ((slope_6m, slope_1m, avg_month, avg_week, volume, high, low, moment, avg_5_sell_orders, avg_5_buy_orders, spread, mid_price, spread_percent, bid_depth), filtred_history)
        """
        return self.strategy.processing(**kwargs)


def test_eva():
    """Тестовая функция"""
    from core.Parsers import SteamMarketParser
    from core.init import init_environment
    from core.logging_config import setup_logging
    
    MODULE_NAME = "Strategy"
    
    setup_logging(
        module_name=MODULE_NAME,
        log_file=f"logs/{MODULE_NAME}.log",
        level=logging.DEBUG
    )

    session, cookies, db = init_environment()
    
    SKIN_FOR_TEST_DUMP = 'M4A1-S | Flashback (Field-Tested)'
    SKIN_FOR_TEST = 'USP-S | Blueprint (Well-Worn)'

    skin_info = db.get_test_skin(SKIN_FOR_TEST)
    
    parser = SteamMarketParser(session, cookies, db)
    parser.load_skin(skin_info)
    log.debug(f"skin_info:{skin_info}")
    
    history, buy_orders, sell_orders = parser.get_buy_data()
    
    
    pt_model = PTModel(model_type="EVA", db=db)
    
    y, amount = pt_model.decide(
        history=history,
        buy_orders=buy_orders,
        sell_orders=sell_orders,
        skin=skin_info
    )
    
    if y is not None:
        log.info(f"price={y:.2f}₸, amount={amount}")
    else:
        log.info("no buy decision made")



if __name__ == "__main__":
    test_eva()