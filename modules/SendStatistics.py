#!/usr/bin/env python3
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
import requests, os

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
        text = self.summarize_transactions(inf)
        if text is not None:
            self.send_message_telegram(text)
        
    def summarize_transactions(self, events):
        """
        events — список кортежей:
        (id, parent_id, event_type, amount, price, created_at, analysis_id, name)
        Каждая сделка = 4 строки подряд: BUY_PLACED, BUY_FILLED, SELL_PLACED, SELL_FILLED
        """
        if len(events) < 4:
            return None
        full_blocks = """💰Today transactions(24h):\n\n"""
        for i in range(0, len(events), 4):
            batch = events[i:i+4]
            if len(batch) < 4:
                continue  # на всякий случай
            
            buy_placed, buy_filled, sell_placed, sell_filled = batch

            name = buy_placed[7]

            # Разницы по цене
            price_diff = sell_filled[4] - buy_filled[4]
            percent_diff = (price_diff / buy_filled[4]) * 100

            # Разницы по времени
            buy_duration = buy_filled[5] - buy_placed[5]
            sell_duration = sell_filled[5] - sell_placed[5]
            
            buy_duration_str = self.format_duration(buy_duration)
            sell_duration_str = self.format_duration(sell_duration)
            # analysis_id всех событий
            analysis_ids = [buy_placed[6], buy_filled[6], sell_placed[6], sell_filled[6]]

            # build block
            block = f"""{name}
  Price diff: {price_diff:.2f}
  Percent diff: {percent_diff:.2f}%
  Durations: buy={buy_duration_str}, sell={sell_duration_str}
  Analysis IDs: {', '.join(str(a) for a in analysis_ids)}\n
            """
            full_blocks += block
        return full_blocks
    
    @staticmethod
    def format_duration(td):
        """
        td — объект timedelta
        возвращает строку вида "Xd Yh Zm"
        """
        total_seconds = int(td.total_seconds())  # игнорируем дробные секунды
        days, remainder = divmod(total_seconds, 86400)  # 86400 секунд в дне
        hours, remainder = divmod(remainder, 3600)      # 3600 секунд в часе
        minutes, _ = divmod(remainder, 60)             # оставляем только минуты
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0 or days > 0:
            parts.append(f"{hours}h")
        parts.append(f"{minutes}m")
        return " ".join(parts)
    
    def send_message_telegram(self, text):
        tg_chat_ids = os.getenv('TG_CHAT_IDS')
        chat_ids = [cid.strip() for cid in tg_chat_ids.split(",") if cid.strip()]
        token = os.getenv("TG_BOT_TOKEN")
        for chat_id in chat_ids:
            try:
                requests.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": text
                    },
                    timeout=5
                )
            except Exception as e:
                log.error(f"error: {e}")


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