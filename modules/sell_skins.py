#!/usr/bin/env python3
"""
Автоматическая продажа скинов из инвентаря
Запускается по расписанию через cron
"""
import sys
import logging
from pathlib import Path
import time
import random

# добавляем корень проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.init import init_environment
from core.logging_config import setup_logging, install_global_exception_handler
from core.Parsers import SteamMarketParser
from modules.SkinChecker import SkinChecker
from core.steam.sell import sell_skin
from core.steam.confirmation import accept_all_confirmations
from core.steam.cookies import get_identity_secret
from analysis.strategies import PTModel


log = logging.getLogger("sell_skins")


# === Конфигурация ===
class Config:
    MIN_FLOAT_VALUE = 0.01
    STEAM_FEE = 0.87
    MIN_MARGIN_PERCENT = 0


# === Фильтры ===
class SkinFilter:
    @staticmethod
    def bef_should_skip(float_value):
        if float_value is None:
            return True, "float is None"
        return False, ""
    @staticmethod
    def aft_should_skip(float_value, marketable_time, item_name_id):
        if float_value < Config.MIN_FLOAT_VALUE:
            return True, f"float too low ({float_value:.4f})"
        if marketable_time is not None:
            return True, f"trade locked until {marketable_time}"
        if item_name_id is None:
            return True, "item_name_id is None"
        return False, ""


# === Расчёт цен ===
class PriceCalculator:
    @staticmethod
    def calculate_margin_price(avg_market_price, buy_price):
        if buy_price is None:
            return avg_market_price, None

        expected_profit = (avg_market_price * Config.STEAM_FEE) - buy_price
        margin_percent = (expected_profit / buy_price) * 100

        if margin_percent < Config.MIN_MARGIN_PERCENT:
            sell_price = buy_price / Config.STEAM_FEE
        else:
            sell_price = avg_market_price

        return sell_price, margin_percent

    
# === Основная логика ===
class SkinSeller:
    """Автоматическая продажа скинов из инвентаря"""

    def __init__(self, session, cookies, db):
        self.session = session
        self.cookies = cookies
        self.db = db
        
        self.parser = SteamMarketParser(session, cookies, db)
        
        self.stats = {
            "total": 0,
            "skipped": 0,
            "new_skins": 0,
            "sold": 0,
            "failed": 0
        }
        

        self.model = PTModel("EVA", db)
        self.order_events = []
        self.new_items = []

    def run(self) -> int:
        """Основная логика модуля"""
        log.info("Fetching inventory")
        
        inventory = self.parser.get_inventory()
        self.inventory = inventory
        
        if inventory is None:
            log.critical("Failed to fetch inventory")
            return 1
        
        self.stats["total"] = len(inventory)
        log.info(f"Found {len(inventory)} items in inventory")
        
        if len(inventory) == 0:
            log.info("Inventory is empty, nothing to sell")
            return 0
        
        # получаем данные о скинах из БД
        skins_db = self.db.get_skins(inventory)
        
        # обрабатываем каждый скин
        for skin in inventory:
            try:
                self._process_single_skin(skin, skins_db)
            except Exception as e:
                log.error(f"Failed to process skin: {e}", exc_info=True)
                self.stats["failed"] += 1
        
        # принимаем все подтверждения
        log.info("Accepting all confirmations")
        try:
            accept_all_confirmations(
                self.session,
                self.cookies,
                get_identity_secret()
            )
        except Exception as e:
            log.error(f"Failed to accept confirmations: {e}", exc_info=True)
        
        self._print_summary()
        
        # exit code: 0 если всё ок, 1 если были фейлы
        return 1 if self.stats["failed"] > 0 else 0

    def _process_single_skin(self, skin, skins_db):
        """Обработка одного скина"""
        skin_name, classid, instanceid, asset_id, marketable_time, float_value, int_value = skin
        buy_price = None
        
        idx = self.stats["skipped"] + self.stats["sold"] + self.stats["failed"] + 1
        log.info(f"[{idx}/{self.stats['total']}] Processing: {skin_name}")
        # проверяем можно ли продавать
        should_skip, reason = SkinFilter.bef_should_skip(float_value)
        
        if should_skip:
            log.info(f"Skipped {skin_name}: {reason}")
            self.stats["skipped"] += 1
            return
        
        # проверяем есть ли скин в БД
        skin_data = skins_db.get(skin_name)
        
        if skin_data is None:
            log.info(f"New skin detected, adding to DB: {skin_name}")
            self.db.add_skin(skin_name)
            self.db.commit()
            self.new_items.append(skin_name)
            self.stats["new_skins"] += 1
            self.stats["skipped"] += 1
            return
        
        item_name_id = skin_data[4]
        
        buy_price = skin_data[7]
        
        # проверяем можно ли продавать
        should_skip, reason = SkinFilter.aft_should_skip(float_value, marketable_time, item_name_id)
        
        if should_skip:
            log.info(f"Skipped {skin_name}: {reason}")
            self.stats["skipped"] += 1
            return
        
        # получаем рыночную цену
        try:
            self.parser.load_skin(skin_data)
            history, buy_orders, sell_orders = self.parser.get_data()
            
            processing_data, _, analysis_id = self.model.processing(history=history, buy_orders=buy_orders, sell_orders=sell_orders, skin=skin_data)
            
            is_legacy = buy_price is None
            
            if not is_legacy:
                self.order_events.append(['BUY_FILLED', skin_name, buy_price, 1, analysis_id])
            
            avg_week = processing_data[3]
            avg_sell_price = processing_data[8]
            
            avg_market_price = max(avg_week, avg_sell_price) * 1.01

            log.info(
                "avg_week=%.2f avg_sell=%.2f target=%.2f",
                avg_week, avg_sell_price, avg_market_price
            )
            
        except Exception as e:
            log.error(f"Market data error for {skin_name}: {e}", exc_info=True)
            self.stats["failed"] += 1
            return
        
        # рассчитываем цену продажи
        sell_price, margin = PriceCalculator.calculate_margin_price(
            avg_market_price, buy_price
        )
        
        if margin is not None:
            log.info(
                f"Pricing {skin_name} | buy={buy_price} avg={avg_market_price} "
                f"margin={margin:+}% sell={sell_price}"
            )
        else:
            log.info(f"Pricing {skin_name} | sell={sell_price}")
        
        # выставляем на продажу
        success = sell_skin(sell_price, asset_id, self.cookies)
        
        if success:
            if not is_legacy:
                self.order_events.append(['SELL_PLACED', skin_name, sell_price, 1, analysis_id])
            else:
                log.warning(f"legacy_sell: {skin_name}")
            log.info(f"Listed successfully: {skin_name}")
            self.stats["sold"] += 1
        else:
            log.error(f"Failed to list: {skin_name}")
            self.stats["failed"] += 1

    def _print_summary(self):
        log.info("=" * 50)
        log.info("EXECUTION SUMMARY")
        log.info(f"Total items:    {self.stats['total']}")
        log.info(f"Listed:         {self.stats['sold']}")
        log.info(f"Skipped:        {self.stats['skipped']}")
        log.info(f"New skins:      {self.stats['new_skins']}")
        log.info(f"Failed:         {self.stats['failed']}")
        log.info("=" * 50)


def main():
    """Точка входа модуля"""
    from dotenv import load_dotenv
    
    # 1. Загружаем .env
    load_dotenv()
    
    # 2. Настраиваем логирование
    MODULE_NAME = "sell_skins"
    setup_logging(
        module_name=MODULE_NAME,
        log_file=f"logs/{MODULE_NAME}.log",
        level=logging.DEBUG
    )
    
    # 3. Устанавливаем exception handler
    install_global_exception_handler(MODULE_NAME)
    
    log.info("=" * 60)
    log.info(f"Starting {MODULE_NAME}")
    log.info("=" * 60)
    
    try:
        # инициализируем окружение
        session, cookies, db = init_environment()
        
        # создаём и запускаем модуль
        seller = SkinSeller(session, cookies, db)
        exit_code = seller.run()
        inventory = seller.inventory
        
        log.info(f"SkinSeller finished with exit code {exit_code}")
        
        sleep_time = random.uniform(3, 6)
        log.info(f"sleep bef start SkinChecker: {round(sleep_time)}")
        time.sleep(sleep_time)
        
        order_events = seller.order_events
        log.info(f"order_events: {order_events}")
        if len(order_events) > 0:
            checker = SkinChecker(session, cookies, db, order_events, inventory)
            checker.run()
        sys.exit(exit_code)
        
        db.close()
        log.info(f"SkinChecker finished with exit code {exit_code}")
    except KeyboardInterrupt:
        log.warning("Interrupted by user")
        sys.exit(130)
        
    except Exception as e:
        log.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()