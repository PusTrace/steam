import sys
import logging
from pathlib import Path

# добавляем корень проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.init import init_environment
from core.logging_config import setup_logging, install_global_exception_handler
from core.Parsers import SteamMarketParser
from analysis.strategies import PTModel


log = logging.getLogger("SkinChecker")

class SkinChecker:
    def __init__(self, session, cookies, db, order_events=None, inventory=None):
        self.session = session
        self.cookies = cookies
        self.db = db
        
        self.parser = SteamMarketParser(session, cookies, db)
        self.model = PTModel("EVA", db)
        
        self.stats = {
            "BUY_FILLED": 0,
            "SELL_PLACED": 0,
            "SELL_FILLED": 0,
            "SKIPPED": 0
        }
        if order_events:
            self.order_events = order_events
        if inventory: 
            self.inventory = inventory
        else:
            self.inventory = self.parser.get_inventory()
        total_orders, wallet, buy_orders, self.sell_orders = self.parser.check_my_state()
        self.my_history, _ = self.parser.get_my_history()
        
        self.buy_filled_arr = []
        self.sell_placed_arr = []
        self.sell_filled_arr = []
    
    def run(self):
        try:
            self._check_new_items()
            
            self.stats["BUY_FILLED"] = len(self.buy_filled_arr)
            self.db.insert_filled_bulk(self.buy_filled_arr)
            
            self.stats["SELL_PLACED"] = len(self.sell_placed_arr)
            self.db.insert_filled_bulk(self.sell_placed_arr)
            
            self.update_sell_filled(_without_print=True)
            self._print_summary()
            
        except Exception as e:
            log.error(f"error: {e}")
            self._print_summary()
        
        
    
    def update_sell_filled(self, _without_print=False):
        try:
            dict_sell_filled = self._check_old_items()
            if len(dict_sell_filled) > 0:
                self._build_sell_filled(dict_sell_filled)
                self.stats["SELL_FILLED"] = len(self.sell_filled_arr)
                log.debug(f"sell_filled: {self.sell_filled_arr[0]}")
                self.db.insert_filled_bulk(self.sell_filled_arr)
                if not _without_print:
                    self._print_summary()
            else:
                log.info("Nothing update")
        except Exception as e:
            log.error(f"error: {e}")
            if not _without_print:
                self._print_summary()
        
    def _build_sell_filled(self, dict_sell_filled):
        skin_data = self.db.get_skins_without_price(dict_sell_filled)

        for raw in skin_data:
            self.parser.load_skin(raw)
            history, buy_orders, sell_orders = self.parser.get_data()
            processing_data, _, analysis_id = self.model.processing(history=history, buy_orders=buy_orders, sell_orders=sell_orders, skin=skin_data[0])
            
            name = raw[1]
            my_history_raw = dict_sell_filled.get(name)
            price = my_history_raw[2]
            
            
        
            sell_filled_str = ["SELL_FILLED", name, price, 1, analysis_id]
            self.sell_filled_arr.append(sell_filled_str)
    
    def _check_old_items(self):
        sell_placed_events = self.db.get_sell_placed_events()
        dict_sell_filled = {}
        
        for raw in sell_placed_events:
            loc, my_history_raw = self._find_in(raw, self.my_history, 1)
            log.debug(f"my_history_raw: {my_history_raw}")
            if loc:
                dict_sell_filled[raw[1]] = my_history_raw
            else:
                log.debug("item is not filled")
        
        return dict_sell_filled
                
        
    
    def _check_new_items(self):
        for raw in self.order_events: # 'BUY_FILLED', skin_name, buy_price, 1, analysis_id
            if raw[0] == 'BUY_FILLED':
                inventory, _ = self._find_in(raw, self.inventory, 0)
                sell_orders, _ = self._find_in(raw, self.sell_orders, 'name')
                if inventory or sell_orders:
                    log.debug('skin in inventory')
                    self.buy_filled_arr.append(raw)
                else:
                    self.stats["SKIPPED"] = +1
                    log.error(f"{raw[1]} not found in inventory or sell_orders")
        for raw in self.order_events:
            if raw[0] == 'SELL_PLACED':
                location, _ = self._find_in(raw, self.sell_orders, 'name')
                if location:
                    next_location = False
                    log.debug('skin in sell_orders')
                    self.sell_placed_arr.append(raw)
                else:
                    next_location = True
                    log.debug(f"{raw[1]} not found in sell_orders table")
                
                if next_location:
                    location, _ = self._find_in(raw, self.my_history, 1)
                    if location:
                        log.debug('skin in my_history')
                        self.sell_placed_arr.append(raw)
                        raw[0] = "SELL_FILLED"
                        self.sell_filled_arr.append(raw)
                    else:
                        self.stats["SKIPPED"] = +1
                        log.error(f"{raw[1]} not found in sell_orders & my_history")
    
    def _print_summary(self):
        log.info(f"BUY_FILLED:      {self.stats['BUY_FILLED']}")
        log.info(f"SELL_PLACED:     {self.stats['SELL_PLACED']}")
        log.info(f"SELL_FILLED:     {self.stats['SELL_FILLED']}")
        log.info(f"Skipped:         {self.stats['SKIPPED']}")


    @staticmethod
    def _find_in(raw, where, index_name):
        log.debug(f"name: {raw[1]}")
        for item in where:
            if item[index_name] == raw[1]:
                return True, item
        return False, None
    



def main():
    """Точка входа модуля"""
    from dotenv import load_dotenv
    
    # 1. Загружаем .env
    load_dotenv()
    
    # 2. Настраиваем логирование
    MODULE_NAME = "SkinChecker"
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
        
        checker = SkinChecker(session, cookies, db)
        checker.update_sell_filled()
        
        db.close()
        
    except KeyboardInterrupt:
        log.warning("Interrupted by user")
        sys.exit(130)
        
    except Exception as e:
        log.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()