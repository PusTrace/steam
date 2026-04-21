#!/usr/bin/env python3
"""
Автоматическое выставление buy-ордеров
Запускается по расписанию через cron
"""

import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# добавляем корень проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.init import init_environment
from core.logging_config import setup_logging, install_global_exception_handler
from analysis.strategies import PTModel
from core.Parsers import SteamMarketParser
from core.steam.api import create_buy_order
from core.steam.confirmation import accept_all_confirmations
from core.steam.cookies import get_identity_secret
from core.my_data_classes import load_config

log = logging.getLogger("place_orders")


class OrderPlacer:
    """Автоматическое размещение buy-ордеров"""

    def __init__(self, session, cookies, db):
        self.session = session
        self.cookies = cookies
        self.db = db
        self.parser = SteamMarketParser(session, cookies, db)
        self.agent = PTModel("EVA", db)

        self.stats = {"total": 0, "placed": 0, "skipped": 0, "failed": 0}
        self.filtred_skins_arr = []
        self.config = load_config("config/config.yaml")
        self.user_want_skins_arr = []

    def should_run(self):
        """Проверяем, есть ли смысл запускаться"""
        log.debug("start check_my_state")
        total_orders, wallet, my_orders, _ = self.parser.check_my_state()

        money_space = wallet * 10 - total_orders

        if money_space < 500:
            return False, money_space, [], wallet

        log.info(f"Money space available: {money_space:.2f}")

        my_orders_names = [a.get("name") for a in my_orders]
        return True, money_space, my_orders_names, wallet

    def run(self):
        """Основная логика модуля"""
        # проверяем нужно ли запускаться
        can_run, money_space, my_orders, wallet = self.should_run()
        if not can_run:
            log.info(f"Not enough space, {money_space:.2f} < 500")
            return 0  # exit code 0 = success (но ничего не сделали)

        # получаем скины для обработки
        filtred_skins = self.db.get_filtered_skins(
            my_orders=my_orders
        )  # TODO: change get filtred skins logic

        self.stats["total"] = len(filtred_skins)

        log.info(f"Found {len(filtred_skins)} skins to process")

        for idx, skin in enumerate(filtred_skins, 1):
            try:
                skin_name, price, amount, analysis_id = self._process_skin(skin, idx)
                self.filtred_skins_arr.append(
                    {
                        "name": skin_name,
                        "price": price,
                        "amount": amount,
                        "analysis_id": analysis_id,
                    }
                )
            except Exception as e:
                log.error(f"Failed to process skin {skin[1]}: {e}", exc_info=True)
                self.stats["failed"] += 1

        user_wants = self.config.place_orders.user_want
        user_item_id = 0
        for user_item in user_wants:
            user_item_id += 1
            filtred_skins = self.db.get_user_want_skin(
                my_orders=my_orders, user_want=user_item
            )  # TODO: get user want logic

            self.stats["total"] += len(filtred_skins)

            log.info(f"Found {len(filtred_skins)} skins to process")

            for idx, skin in enumerate(filtred_skins, 1):
                try:
                    skin_name, price, amount, analysis_id = self._process_skin(
                        skin, idx
                    )
                    self.user_want_skins_arr.append(
                        {
                            "name": skin_name,
                            "price": price,
                            "amount": amount,
                            "analysis_id": analysis_id,
                            "id": user_item_id,
                        }
                    )
                except Exception as e:
                    log.error(f"Failed to process skin {skin[1]}: {e}", exc_info=True)
                    self.stats["failed"] += 1

        # buy_arr = calculate skins TODO: need calculate and select best skins for buy

        self._place_orders(buy_arr)
        self._print_summary()

        # exit code: 0 если всё ок, 1 если были фейлы
        return 1 if self.stats["failed"] > 0 else 0

    def _process_skin(self, skin, idx):
        """Обработка одного скина"""
        skin_name = skin[1]
        log.debug(f"skin: {skin}")
        log.info(f"[{idx}/{self.stats['total']}] Processing: {skin_name}")

        self.parser.load_skin(skin)
        history, buy_orders, sell_orders = self.parser.get_data()

        price, amount, analysis_id = self.agent.decide(
            history=history, buy_orders=buy_orders, sell_orders=sell_orders, skin=skin
        )

        if price is None:
            log.info(f"Agent decided to skip: {skin_name}")
            self.stats["skipped"] += 1
            return

    def _place_orders(self, buy_arr):
        name, price, amount, analysis_id = buy_arr
        log.info(f"Placing order: {skin_name} @ {price:.2f} x{amount}")

        response = create_buy_order(self.cookies, skin_name, price, amount)

        if self._handle_response(response, skin_name, price, amount):
            self.stats["placed"] += 1
            self.db.buy_placed(skin_name, price, amount, analysis_id)
            self.db.commit()
        else:
            self.stats["failed"] += 1

    def _handle_response(self, response, skin_name, price, amount):
        """Обработка ответа Steam API"""
        if response.status_code == 200:
            data = response.json()

            if data.get("success") == 29:
                log.warning(f"Order already exists: {skin_name}")
                return False

            if data.get("success") == 25:
                log.error(f"Money limit reached: {skin_name}")
                sys.exit(1)  # критическая ошибка, останавливаем модуль

            log.info(f"Order placed successfully: {skin_name}")
            return True

        elif response.status_code == 406:
            # нужна конфирмация
            return self._handle_confirmation(response, skin_name, price, amount)

        else:
            log.error(f"Unexpected status {response.status_code} for {skin_name}")
            return False

    def _handle_confirmation(self, response, skin_name, price, amount):
        """Обработка подтверждения через mobile authenticator"""
        data = response.json()
        conf_id = int(data.get("confirmation", {}).get("confirmation_id", 0))

        if not conf_id:
            log.error(f"Missing confirmation_id for {skin_name}")
            return False

        log.info(f"Accepting confirmation for {skin_name}")

        accept_all_confirmations(self.session, self.cookies, get_identity_secret())

        # повторяем запрос
        retry = create_buy_order(self.cookies, skin_name, price, amount, conf_id)

        if retry.status_code == 200:
            log.info(f"Order placed after confirmation: {skin_name}")
            return True

        log.error(f"Failed after confirmation: {skin_name}")
        return False

    def _print_summary(self):
        log.info("EXECUTION SUMMARY")
        log.info(f"Total skins:    {self.stats['total']}")
        log.info(f"Orders placed:  {self.stats['placed']}")
        log.info(f"Skipped:        {self.stats['skipped']}")
        log.info(f"Failed:         {self.stats['failed']}")


def main():
    """Точка входа модуля"""
    load_dotenv()
    # настраиваем логирование
    MODULE_NAME = "place_orders"
    setup_logging(
        module_name=MODULE_NAME, log_file=f"logs/{MODULE_NAME}.log", level=logging.DEBUG
    )

    # устанавливаем глобальный обработчик исключений
    install_global_exception_handler(MODULE_NAME)

    log.info(f"Starting {MODULE_NAME}")

    try:
        # инициализируем окружение
        session, cookies, db = init_environment()

        # создаём и запускаем модуль
        placer = OrderPlacer(session, cookies, db)
        log.debug("order_placer created")
        exit_code = placer.run()

        db.close()

        log.info(f"Module finished with exit code {exit_code}")
        sys.exit(exit_code)

    except KeyboardInterrupt:
        log.warning("Interrupted by user")
        sys.exit(130)  # стандартный код для Ctrl+C

    except Exception as e:
        log.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
