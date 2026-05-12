# tests/test_parser.py

import pytest

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.Parsers import SteamMarketParser
import core.objects as obj


@pytest.mark.parametrize(
    "skin_name",
    [
        "USP-S | Blueprint (Well-Worn)",
        "M4A1-S | Flashback (Field-Tested)",
        "USP-S | Whiteout (Factory New)",
    ],
)
def test_parser_returns_market_data(
    environment,
    config,
    skin_name,
):

    session, db = environment

    raw_skin = db.get_test_skin(skin_name)

    skin = obj.Skin.model_validate(raw_skin)

    parser = SteamMarketParser(
        session=session,
        db=db,
        config=config,
    )

    parser.load_skin(skin)

    market_data = parser.get_data()

    assert market_data is not None

    assert len(market_data.history) > 0

    assert len(market_data.buy_orders) > 0

    assert len(market_data.sell_orders) > 0

    assert market_data.skin.name == skin_name
