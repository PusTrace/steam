#!/usr/bin/env python3
"""
Автоматическая продажа скинов из инвентаря
Запускается по расписанию через cron
"""

import os
import sys
import logging
from pathlib import Path

# добавляем корень проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))


from core import db
from core.logging_config import setup_logging, install_global_exception_handler
from analysis.strategies import PTModel
import core.models as obj
from SteamAPI import SteamAPI
from core.db import PostgreSQLDB

log = logging.getLogger("sell_skins")


# === Основная логика ===
class SkinSeller:
    """Автоматическая продажа скинов из инвентаря"""

    def __init__(self):
        secrets = obj.load_secrets()
        cfg = obj.load_config()

        self.db = PostgreSQLDB(host=secrets.db_host, password=secrets.db_password)
        self.api = SteamAPI(secrets=secrets, config=cfg)
        self.model = PTModel("EVA")

        self.secrets = secrets
        self.cfg = cfg.sell_skins
        self.cfg = cfg.sell_skins

        self.stats = {"total": 0, "skipped": 0, "new_skins": 0, "sold": 0, "failed": 0}
        self.order_events = []
        self.new_items = []

    def run(self) -> int:
        """Основная логика модуля"""
        log.debug("Fetching inventory")

        inventory = self.api.market.get_inventory()
        self.inventory = inventory

        if inventory is None:
            log.critical("Failed to fetch inventory")
            return 1

        self.stats["total"] = len(inventory)
        log.info(f"Found {len(inventory)} items in inventory")

        if len(inventory) == 0:
            log.error("Inventory is empty, nothing to sell")
            return 0

        # получаем данные о скинах из БД
        skins_db = self.db.get_skins(inventory)

        # обрабатываем каждый скин
        for skin in inventory:
            db_skin = None
            for db_skin in skins_db:  # TODO: db skin must be obj.Skin
                if db_skin["name"] == skin.name:
                    break
                else:
                    continue
            if db_skin is None:
                log.info(f"New skin detected, adding to list: {skin.name}")
                self.new_items.append(skin.name)
                self.stats["new_skins"] += 1
                continue
            try:
                self._process_single_skin(skin, db_skin)
                exit(1)
            except Exception as e:
                log.error(f"Failed to process skin: {e}", exc_info=True)
                self.stats["failed"] += 1
                exit(1)

        # принимаем все подтверждения
        log.info("Accepting all confirmations")
        try:
            self.api.conf.accept_all()
        except Exception as e:
            log.error(f"Failed to accept confirmations: {e}", exc_info=True)

        self._print_summary()

        # exit code: 0 если всё ок, 1 если были фейлы
        return 1 if self.stats["failed"] > 0 else 0

    def _process_single_skin(self, skin, db_skin):
        """Обработка одного скина"""
        idx = self.stats["skipped"] + self.stats["sold"] + self.stats["failed"] + 1
        log.info(f"[{idx}/{self.stats['total']}] Processing: {skin.name}")
        # проверяем можно ли продавать
        if skin.float_value is None:
            log.debug(f"Skipped {skin.name}: float is none")
            self.stats["skipped"] += 1
            return

        # проверяем есть ли скин в БД
        db_skin = obj.Skin.model_validate(db_skin)

        item_name_id = db_skin.item_name_id
        buy_price = db_skin.buy_price

        # проверяем можно ли продавать
        if skin.float_value < self.cfg.min_float_value:
            log.info(f"float too low ({skin.float_value:.4f})")
            self.stats["skipped"] += 1
            return
        if skin.marketable_time is not None:
            log.info(f"trade locked until {skin.marketable_time}")
            self.stats["skipped"] += 1
            return
        if item_name_id is None:
            log.info("item_name_id is None")
            self.stats["skipped"] += 1
            return

        # получаем рыночную цену
        try:
            market_data = self.api.market.get_market_data(skin=db_skin)

            resp = self.model.process(market_data=market_data)
            if resp is None:
                log.error(f"cant processing item: {skin.name}")
                self.stats["failed"] += 1
                return
            processed, _ = resp

            self.order_events.append(["BUY_FILLED", skin.name, buy_price, 1, processed])

            avg_market_price = (
                max(processed.avg_week, processed.avg_5_sell_orders) * 1.01
            )

            log.debug(
                "avg_week=%.2f avg_sell=%.2f target=%.2f",
                processed.avg_week,
                processed.avg_5_sell_orders,
                avg_market_price,
            )
            exit(0)

        except Exception as e:
            log.error(f"Market data error for {skin.name}: {e}", exc_info=True)
            self.stats["failed"] += 1
            exit(0)
            return

        # рассчитываем цену продажи
        sell_price, margin = self.calculate_margin_price(avg_market_price, buy_price)
        log.debug(f"buy={buy_price} margin={margin:+}% sell={sell_price}")

        # выставляем на продажу
        success = self.api.trade.sell_skin(sell_price, skin.asset_id)

        if success:
            self.order_events.append(
                ["SELL_PLACED", skin.name, round(sell_price * 0.87), 1, processed]
            )
            log.info(f"Listed successfully: {skin.name}")
            self.stats["sold"] += 1
        else:
            log.error(f"Failed to list: {skin.name}")
            self.stats["failed"] += 1
        self._print_summary()

    def _print_summary(self):
        log.info("EXECUTION SUMMARY")
        log.info(f"Total items:    {self.stats['total']}")
        if self.stats["sold"]:
            log.info(f"Listed:         {self.stats['sold']}")
        if self.stats["skipped"]:
            log.info(f"Skipped:        {self.stats['skipped']}")
        if self.stats["new_skins"]:
            log.info(f"New skins:      {self.stats['new_skins']}")
        if self.stats["failed"]:
            log.info(f"Failed:         {self.stats['failed']}")

    def calculate_margin_price(self, avg_market_price, buy_price):
        expected_profit = (avg_market_price * self.cfg.steam_fee) - buy_price
        margin_percent = (expected_profit / buy_price) * 100

        if margin_percent < self.cfg.min_margin_percent:
            sell_price = buy_price / self.cfg.steam_fee
        else:
            sell_price = avg_market_price

        return sell_price, margin_percent


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
        level=logging.DEBUG,
        with_telergam=False,
    )

    # 3. Устанавливаем exception handler
    install_global_exception_handler(MODULE_NAME)

    log.info(f"Starting {MODULE_NAME}")

    try:
        # инициализируем окружение

        # создаём и запускаем модуль
        seller = SkinSeller()
        exit_code = seller.run()
        # inventory = seller.inventory

        log.info(f"SkinSeller finished with exit code {exit_code}")

        # sleep_time = random.uniform(3, 6)
        # log.info(f"sleep bef start SkinChecker: {round(sleep_time)}")
        # time.sleep(sleep_time)

        # order_events = seller.order_events
        # if len(order_events) > 0:
        #    checker = SkinChecker(session, cookies, db, order_events, inventory)
        #    checker.run()

        # parser = SoftParser(session=session, cookies=cookies, db=db)

        # sleep_time = random.uniform(3, 6)
        # log.info(f"sleep bef start SoftParser: {round(sleep_time)}")
        # log.info("Running item_nameid update")
        # exit_code = parser.run_update_item_nameids()

        # db.close()
        # log.info(f"SkinChecker finished with exit code {exit_code}")
    except KeyboardInterrupt:
        log.warning("Interrupted by user")
        sys.exit(130)

    except Exception as e:
        log.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        sys.exit(0)


if __name__ == "__main__":
    main()
