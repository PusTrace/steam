#!/usr/bin/env python3
import sys
import logging
from pathlib import Path

# добавляем корень проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.init import init_environment
from core.logging_config import setup_logging, install_global_exception_handler
from core.Parsers import SteamMarketParser


log = logging.getLogger("GetBuyOrders")


class StatusUpdater:
    def __init__(self, session, cookies, db):
        self.session = session
        self.cookies = cookies
        self.db = db
        
        self.parser = SteamMarketParser(session, cookies, db)

        total_orders, wallet, self.buy_orders, sell_orders = self.parser.check_my_state()

    def run(self):
        for dict in self.buy_orders:
            self.db.buy_placed(dict.get("name"), dict.get("price"), dict.get("qty"), 0)


def main():
    """Точка входа модуля"""
    from dotenv import load_dotenv
    
    # 1. Загружаем .env
    load_dotenv()
    
    # 2. Настраиваем логирование
    MODULE_NAME = "GetBuyOrders"
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
        seller = StatusUpdater(session, cookies, db)
        seller.run()
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        log.warning("Interrupted by user")
        sys.exit(130)
        
    except Exception as e:
        log.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()