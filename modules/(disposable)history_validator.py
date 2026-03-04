#!/usr/bin/env python3
import sys
import logging
from pathlib import Path
import time
import random
from datetime import date, datetime
# добавляем корень проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.init import init_environment
from core.logging_config import setup_logging, install_global_exception_handler
from core.Parsers import SteamMarketParser


log = logging.getLogger("sell_skins")
    
# === Основная логика ===
class HistoryValidator:
    """Автоматическая продажа скинов из инвентаря"""

    def __init__(self, session, cookies, db):
        self.session = session
        self.cookies = cookies
        self.db = db
        
        self.parser = SteamMarketParser(session, cookies, db)
        self.full_history = []

    def run(self) -> int:
        """Основная логика модуля"""
        start = 0
        max_retries = 5
        total_count = None
        last_year = 2026
        
        log.debug(f"start date: {date.today()}")
        
        while total_count is None or start < total_count:
            if total_count is None:
                step = 100
            else:  
                if total_count - start > 100:
                    step = 100
                elif total_count - start > 10:
                    step = 10
                else:
                    step = 1

            retries = 0

            while retries < max_retries:
                try:
                    
                    my_history, total_count = self.parser.get_my_history(start, step)
                    
                    log.debug(len(my_history))
                    
                    my_history = self._fix_history_dates(my_history, last_year)
                    
                    last_year = int(my_history[-1][3].split('-')[0])
                    
                    log.debug("%s, %s, %s", my_history[-1][1], last_year, my_history[-1][4])
                                        
                    self.db.insert_my_history(my_history)
                    self.full_history.append(my_history)
                    
                    if retries > 0:
                        sleep_time = random.uniform(3, 6) * retries
                    else:
                        sleep_time = random.uniform(3, 6)
                    
                    log.debug(f"sleep_time: {sleep_time}")
                    
                    time.sleep(sleep_time)
                    # успех → выходим из retry-цикла
                    break

                except Exception as e:
                    retries += 1
                    log.error(f"Ошибка на start={start}, попытка {retries}: {e}")

                    sleep_time = random.uniform(10, 25) * retries
                    time.sleep(sleep_time)

            else:
                # если все попытки исчерпаны
                log.error(f"выход на блоке start={start} после {max_retries} неудачных попыток")
                exit(1)

            # двигаемся дальше ТОЛЬКО если был успех
            start += step
            time.sleep(random.uniform(6, 12))
    
    @staticmethod
    def _fix_history_dates(items, start_year=None):
        """
        items: список списков [assetid, market_name, price, acted_on_str, listed_on_str, gain_loss]
        start_year: если None, берется текущий год
        """
        if start_year is None:
            start_year = date.today().year

        month_map = {
            "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
            "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
            "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
        }

        fixed_items = []

        current_year = start_year
        last_acted_month = None

        for item in items:
            acted_on_str = item[3]  # строка вида "3 Mar"
            listed_on_str = item[4]

            # --- исправляем acted_on ---
            if acted_on_str:
                day, mon = acted_on_str.split()
                month = month_map.get(mon, 1)
                day = int(day)

                # если месяц “прыгает” назад относительно предыдущего acted_on → прошлый год
                if last_acted_month is not None and month > last_acted_month:
                    current_year -= 1

                last_acted_month = month
                acted_on_date = date(current_year, month, day)
            else:
                acted_on_date = None

            # --- исправляем listed_on относительно acted_on ---
            if listed_on_str:
                day, mon = listed_on_str.split()
                month = month_map.get(mon, 1)
                day = int(day)

                # временно считаем listed_on в том же году, что acted_on
                listed_candidate = date(acted_on_date.year if acted_on_date else current_year, month, day)

                # если listed_on > acted_on → прошлый год
                if acted_on_date and listed_candidate > acted_on_date:
                    listed_on_date = date(acted_on_date.year - 1, month, day)
                else:
                    listed_on_date = listed_candidate
            else:
                listed_on_date = None

            fixed_items.append([
                item[0],  # assetid
                item[1],  # market_name
                item[2],  # price
                acted_on_date.isoformat() if acted_on_date else None,
                listed_on_date.isoformat() if listed_on_date else None,
                item[5]   # gain_loss
            ])

        return fixed_items

def main():
    """Точка входа модуля"""
    from dotenv import load_dotenv
    
    # 1. Загружаем .env
    load_dotenv()
    
    # 2. Настраиваем логирование
    MODULE_NAME = "history_validator"
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
        validator = HistoryValidator(session, cookies, db)
        validator.run()
        
        
    except KeyboardInterrupt:
        log.warning("Interrupted by user")
        sys.exit(130)
        
    except Exception as e:
        log.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()