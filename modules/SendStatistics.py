#!/usr/bin/env python3
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
import time
import requests, os
from collections import defaultdict

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

proxies = {
    "http": "http://127.0.0.1:2080",
    "https": "http://127.0.0.1:2080"
}


    
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
        
        lagging_array = os.getenv('LAGGING_DAYS')
        if lagging_array:
            lagging_days = [cid.strip() for cid in lagging_array.split(",") if cid.strip()]
        else:
            lagging_days = ["1"]
        now = datetime.now()
        for lagging_day in lagging_days:
            lagging_day = int(lagging_day) 
            from_date = now - timedelta(hours=lagging_day*24)
            inf = self.db.get_full_transaction(from_date)
            text = self.summarize_transactions(inf, from_date)

            if text is not None:
                self.send_message_telegram(text)

 
    def summarize_transactions(self, events, from_date):

        from_date = from_date + timedelta(days=1)
        full_blocks = f"💰{from_date} transactions:\n\n"

        groups = defaultdict(list)

        # группируем события по transaction id
        for e in events:
            tx = e[1] if e[1] else e[0]
            groups[tx].append(e)

        transactions = []

        for tx, evs in groups.items():

            evs.sort(key=lambda x: x[5])  # сортировка по created_at

            buy_placed = None
            buy_filled = []
            sell_placed = []
            sell_filled = []

            for e in evs:
                if e[2] == "BUY_PLACED":
                    buy_placed = e
                elif e[2] == "BUY_FILLED":
                    buy_filled.append(e)
                elif e[2] == "SELL_PLACED":
                    sell_placed.append(e)
                elif e[2] == "SELL_FILLED":
                    sell_filled.append(e)

            # пропускаем если нет sell
            if not sell_filled or not sell_placed or not buy_filled:
                continue

            count = len(sell_filled)
            for i in range(count):

                if i >= len(buy_filled) or i >= len(sell_placed):
                    continue
                bf = buy_filled[i]
                sf = sell_filled[i]
                sp = sell_placed[i] if i < len(sell_placed) else sell_placed[-1]

                price_diff = sf[4] - bf[4]
                percent_diff = (price_diff / bf[4]) * 100

                buy_duration = bf[5] - buy_placed[5]
                sell_duration = sf[5] - sp[5]

                transactions.append({
                    "name": bf[7],
                    "price_diff": price_diff,
                    "percent_diff": percent_diff,
                    "buy_duration": self.format_duration(buy_duration),
                    "sell_duration": self.format_duration(sell_duration),
                    "analysis_ids": [buy_placed[6], bf[6], sp[6], sf[6]],
                        "time": sf[5]
                    })

        # сортировка транзакций по времени продажи
        transactions.sort(key=lambda x: x["time"])
        if len(transactions) == 0:
            full_blocks = ""
        else:
            for t in transactions:
                block = (
                    f"{t['name']}\n"
                    f"    price diff: {t['price_diff']:.2f}\n"
                    f"    percent diff: {t['percent_diff']:.2f}%\n"
                    f"    durations: buy={t['buy_duration']}, sell={t['sell_duration']}\n"
                    f"    analysis ids: {', '.join(map(str, t['analysis_ids']))}\n\n"
                )
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

        url = f"https://api.telegram.org/bot{token}/sendMessage"

        session = requests.Session()

        for chat_id in chat_ids:
            try:

                response = session.post(
                    url,
                    json={
                        "chat_id": chat_id,
                        "text": text
                    },
                    timeout=5,
                    proxies=proxies
                )

                if response.status_code != 200:
                    msg_empty = response.json()
                    msg_empty = msg_empty.get("description")
                    if msg_empty == "Bad Request: message text is empty":
                        log.debug(msg_empty)
                    else:
                        log.error(f"telegram error {response.status_code}: {response.text}")

                # rate limit
                time.sleep(0.1)

            except Exception as e:
                log.error(f"telegram send error: {e}")


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
