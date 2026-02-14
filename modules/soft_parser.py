#!/usr/bin/env python3
"""
Мягкий парсинг данных Steam Market
Обновляет кеш цен и ордеров для всех скинов в БД
Запускается по расписанию через cron
"""
import sys
import time
from datetime import datetime, timedelta
import random
import logging
from typing import Tuple
from pathlib import Path

# добавляем корень проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.init import init_environment
from core.logging_config import setup_logging, install_global_exception_handler
from core.Parsers import SteamMarketParser
from core.steam.api import get_item_nameid_with_page
from playwright.sync_api import sync_playwright
from analysis.strategies import PTModel


log = logging.getLogger("soft_parser")


# === Основной класс ===
class SoftParser:
    """Парсер для обновления данных о скинах"""

    def __init__(self, session, cookies, db, time_sleep_range: tuple = (1, 2), until_date: str = None):
        self.session = session
        self.cookies = cookies
        self.db = db
        self.until_date = until_date
        
        self.parser = SteamMarketParser(session, cookies, db)
        self.model = PTModel("EVA", db)
        self.time_sleep_range = time_sleep_range
        
        self.stats = {"total": 0, "updated": 0, "skipped": 0, "failed": 0}
        
        self.logger = logging.getLogger("soft_parser.SoftParser")

    def run_update_prices(self) -> int:
        """Обновляет цены и ордера для всех скинов"""
        log.info("Fetching all skins from database")
        
        skins = self.db.get_all_skins(self.until_date)
        self.stats["total"] = len(skins)
        
        log.info(f"Found {len(skins)} skins to update")
        
        if len(skins) == 0:
            log.info("No skins to process")
            return 0
        
        for idx, skin in enumerate(skins, 1):
            try:
                self._process_single_skin(skin, idx)
                
                # задержка между запросами
                delay = random.uniform(*self.time_sleep_range)
                time.sleep(delay)
                
            except Exception as e:
                log.error(f"Failed to process skin: {e}", exc_info=True)
                self.stats["failed"] += 1
        
        self._print_summary()
        
        return 1 if self.stats["failed"] > 0 else 0

    def run_update_item_nameids(self) -> int:
        """Обновляет item_nameid для скинов через Playwright"""
        log.info("Fetching skins without item_nameid")
        
        skins = self.db.get_skins_without_item_nameid()
        self.stats["total"] = len(skins)
        
        log.info(f"Found {len(skins)} skins without item_nameid")
        
        if len(skins) == 0:
            log.info("All skins have item_nameid")
            return 0
        
        log.info("Launching Playwright browser")
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()
                
                # добавляем cookies для авторизации
                context.add_cookies([
                    {
                        "name": k,
                        "value": v,
                        "domain": ".steamcommunity.com",
                        "path": "/",
                        "httpOnly": False,
                        "secure": True
                    }
                    for k, v in self.cookies.items()
                ])
                
                page = context.new_page()
                
                for idx, (skin_name,) in enumerate(skins, 1):
                    try:
                        self._process_single_item_nameid(skin_name, idx, page)
                        
                        # задержка между запросами
                        delay = random.uniform(*self.time_sleep_range)
                        time.sleep(delay)
                        
                    except Exception as e:
                        log.error(f"Failed to process {skin_name}: {e}", exc_info=True)
                        self.stats["failed"] += 1
                
                browser.close()
                
        except Exception as e:
            log.critical(f"Playwright error: {e}", exc_info=True)
            return 1
        
        self._print_summary()
        
        return 1 if self.stats["failed"] > 0 else 0

    def _process_single_skin(self, skin: Tuple, idx: int):
        """Обновление цен и ордеров для одного скина"""
        skin_name = skin[1]
        
        log.info(f"[{idx}/{self.stats['total']}] Updating: {skin_name}")
        
        try:
            self.parser.load_skin(skin)
            history, buy_orders, sell_orders = self.parser.get_data()
            data, _, _ = self.model.processing(history=history, buy_orders=buy_orders, sell_orders=sell_orders, skin=skin)
            
            log.debug(f"Successfully updated: {skin_name}")
            log.debug(f"Updated_data: {data}")
            self.stats["updated"] += 1
            
        except Exception as e:
            log.error(f"Error processing {skin_name}: {e}", exc_info=True)
            self.db.rollback()
            self.stats["failed"] += 1

    def _process_single_item_nameid(self, skin_name: str, idx: int, page):
        """Получение item_nameid через Playwright"""
        log.info(f"[{idx}/{self.stats['total']}] Processing: {skin_name}")
        
        try:
            item_name_id, avg_price = get_item_nameid_with_page(
                skin_name=skin_name,
                page=page
            )
            
            log.debug(f"Got item_name_id={item_name_id} for {skin_name}")
            
            if item_name_id == 0:
                log.error(f"Failed to get item_nameid for: {skin_name}")
                self.stats["failed"] += 1
                
            elif item_name_id == -1:
                log.warning(f"Skin doesn't exist: {skin_name}")
                self.db.remove_skin(skin_name)
                self.db.commit()
                self.stats["skipped"] += 1
                
            else:
                self.db.save_item_name_id(
                    skin_name=skin_name,
                    item_name_id=item_name_id
                )
                self.db.commit()
                log.info(f"Saved item_nameid for: {skin_name}")
                self.stats["updated"] += 1
                
        except Exception as e:
            log.error(f"Error processing {skin_name}: {e}", exc_info=True)
            self.db.rollback()
            self.stats["failed"] += 1

    def _print_summary(self):
        log.info("=" * 50)
        log.info("EXECUTION SUMMARY")
        log.info(f"Total skins:    {self.stats['total']}")
        log.info(f"Updated:        {self.stats['updated']}")
        log.info(f"Skipped:        {self.stats['skipped']}")
        log.info(f"Failed:         {self.stats['failed']}")
        log.info("=" * 50)


def main():
    """Точка входа модуля"""
    from dotenv import load_dotenv
    
    # 1. Загружаем .env
    load_dotenv()
    
    # 2. Настраиваем логирование
    MODULE_NAME = "soft_parser"
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
        
        datetime_days_ago = datetime.now() - timedelta(days=14)
        
        date_days_ago = datetime_days_ago.date()
        
        until_date = str(date_days_ago)
        
        log.info(f"until_date: {until_date}")
        
        
        # создаём парсер
        parser = SoftParser(session=session, cookies=cookies, db=db, until_date=until_date)
        
        # запускаем обновление цен
        log.info("Running price update")
        exit_code = parser.run_update_prices()
        
        # опционально: обновляем item_nameid если нужно
        # log.info("Running item_nameid update")
        # exit_code = parser.run_update_item_nameids()
        
        db.close()
        
        log.info(f"Module finished with exit code {exit_code}")
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        log.warning("Interrupted by user")
        sys.exit(130)
        
    except Exception as e:
        log.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()