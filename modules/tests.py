from dotenv import load_dotenv
import logging
import sys
from pathlib import Path

log = logging.getLogger("TESTS")

# добавляем корень проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.Parsers import SteamMarketParser
from core.init import init_environment
from core.logging_config import setup_logging
import core.objects as obj
from analysis.strategies import PTModel


def test_eva():
    """Тестовая функция"""
    load_dotenv()

    MODULE_NAME = "TESTS"
    setup_logging(
        module_name=MODULE_NAME, log_file=f"logs/{MODULE_NAME}.log", level=logging.DEBUG
    )

    session, _, db = init_environment()

    # SKIN_FOR_TEST_DUMP = "M4A1-S | Flashback (Field-Tested)"
    SKIN_FOR_TEST = "USP-S | Blueprint (Well-Worn)"

    raw_skin = db.get_test_skin(SKIN_FOR_TEST)
    skin = obj.Skin.model_validate(raw_skin)

    parser = SteamMarketParser(session=session, db=db, config=obj.load_config())
    parser.load_skin(skin)

    log.debug(f"skin:{skin.name}")

    market_data = parser.get_data()

    pt_model = PTModel(model_type="EVA")

    price, amount = pt_model.decide(market_data=market_data)

    if price is not None:
        log.info(f"price={price:.2f}₸, amount={amount}")
    else:
        log.info("no buy decision made")


if __name__ == "__main__":
    test_eva()
