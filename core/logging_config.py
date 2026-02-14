"""
Централизованная настройка логирования
- Файлы для каждого модуля
- Телеграм для критических ошибок
- Rotated logs
"""
import os
import sys
import logging
import requests
from logging.handlers import RotatingFileHandler
from pathlib import Path
from dotenv import load_dotenv


class TelegramHandler(logging.Handler):
    """
    Отправляет ERROR и CRITICAL в телеграм
    С указанием модуля и контекста
    """
    def __init__(self, token: str, chat_ids: list[str], module_name: str, timeout=5):
        super().__init__(level=logging.ERROR)
        self.token = token
        self.chat_ids = chat_ids
        self.module_name = module_name
        self.timeout = timeout
        self.api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)

            emoji = "🔥" if record.levelno >= logging.CRITICAL else "⚠️"

            text = (
                f"{emoji} *{record.levelname}* | `{self.module_name}`\n\n"
                f"```\n{msg}\n```"
            )

            for chat_id in self.chat_ids:
                requests.post(
                    self.api_url,
                    json={
                        "chat_id": chat_id,
                        "text": text,
                        "parse_mode": "Markdown"
                    },
                    timeout=self.timeout
                )
        except Exception:
            # логгер никогда не должен валить приложение
            pass


def setup_logging(
    module_name: str,
    log_file: str = None,
    level: int = logging.INFO,
    file_level: int = None,
    console_level: int = None,
    with_telergam: bool = True
):
    file_level = file_level or level
    console_level = console_level or level
    
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers.clear()
    
    # === КОНСОЛЬ ===
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # === ФАЙЛ ===
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(file_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    if with_telergam:
        # === ТЕЛЕГРАМ ===
        token = os.getenv("TG_BOT_TOKEN")
        chat_ids_raw = os.getenv("TG_CHAT_IDS")

        if token and chat_ids_raw:
            chat_ids = [cid.strip() for cid in chat_ids_raw.split(",") if cid.strip()]

            telegram_handler = TelegramHandler(token, chat_ids, module_name)
            telegram_handler.setFormatter(formatter)
            root_logger.addHandler(telegram_handler)

            logging.info(f"Telegram notifications enabled for {module_name}: {chat_ids}")
        else:
            logging.warning("Telegram notifications disabled (missing credentials)")
    
    logging.info(f"Logging initialized for module: {module_name}")


def install_global_exception_handler(module_name: str):
    """
    Все uncaught exceptions логируются и уходят в телеграм
    """
    def excepthook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        log = logging.getLogger("UNCAUGHT")
        log.critical(
            f"Uncaught exception in {module_name}",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
        sys.exit(1)
    
    sys.excepthook = excepthook


if __name__ == "__main__":
    load_dotenv()

    MODULE_NAME = "LOGGER_TEST"

    setup_logging(
        module_name=MODULE_NAME,
        log_file="logs/test.log",
        level=logging.DEBUG
    )

    install_global_exception_handler(MODULE_NAME)

    log = logging.getLogger(MODULE_NAME)

    log.info("Info message (no telegram)")
    log.warning("Warning message (no telegram)")
    log.error("Error message (should go to telegram)")
    log.critical("Critical message (should go to telegram)")

    log.info("Raising exception to test global handler...")
    raise RuntimeError("Boom! Uncaught exception test")
