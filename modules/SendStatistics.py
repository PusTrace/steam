#!/usr/bin/env python3
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta

# добавляем корень проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.init import init_environment
from core.logging_config import setup_logging, install_global_exception_handler
from core.Parsers import SteamMarketParser
from core.steam.sell import sell_skin
from core.steam.confirmation import accept_all_confirmations
from core.steam.cookies import get_identity_secret
from analysis.strategies import PTModel


log = logging.getLogger("SendStatistics")



    
# === Основная логика ===
class SendStatistics:
    """Автоматическая продажа скинов из инвентаря"""

    def __init__(self, session, cookies, db):
        self.session = session
        self.cookies = cookies
        self.db = db

    def run(self) -> int:
        """Основная логика модуля"""
        log.info("Fetching 24h information")
        now = datetime.now()
        from_date = now - timedelta(hours=24)
        inf = self.db.get_full_transaction(from_date)
        log.info(inf)
   


def main():
    """Точка входа модуля"""
    from dotenv import load_dotenv
    
    # 1. Загружаем .env
    load_dotenv()
    
    # 2. Настраиваем логирование
    MODULE_NAME = "SendStatistics"
    setup_logging(
        module_name=MODULE_NAME,
        log_file=f"logs/{MODULE_NAME}.log",
        level=logging.DEBUG
    )
    
    # 3. Устанавливаем exception handler
    install_global_exception_handler(MODULE_NAME)
    
    log.info(f"Starting {MODULE_NAME}")
    
    try:
        # инициализируем окружение
        session, cookies, db = init_environment()
        
        # создаём и запускаем модуль
        sender = SendStatistics(session, cookies, db)
        sender.run()
        
    except KeyboardInterrupt:
        log.warning("Interrupted by user")
        sys.exit(130)
        
    except Exception as e:
        log.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()