import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.init import init_environment
from core import objects as obj
from api.api import SteamAPI

# ─────────────────────────────────────────────────────────────────── #
#  Низкоуровневые фикстуры                                            #
# ─────────────────────────────────────────────────────────────────── #


@pytest.fixture(scope="session")
def config() -> obj.Config:
    return obj.load_config()


@pytest.fixture(scope="session")
def environment():
    load_dotenv()
    session, _, db = init_environment()
    return session, db


@pytest.fixture(scope="session")
def db(environment):
    _, db = environment
    return db


# ─────────────────────────────────────────────────────────────────── #
#  API-фикстуры                                                       #
# ─────────────────────────────────────────────────────────────────── #


@pytest.fixture(scope="session")
def api(environment, config) -> SteamAPI:
    session, _ = environment
    return SteamAPI(session, config)


@pytest.fixture(scope="session")
def market(api):
    return api.market


@pytest.fixture(scope="session")
def client(api):
    return api.market.client


@pytest.fixture(scope="session")
def parser(api):
    return api.market.parser


# ─────────────────────────────────────────────────────────────────── #
#  Тестовые скины                                                     #
# ─────────────────────────────────────────────────────────────────── #

TEST_SKIN_NAMES = [
    "USP-S | Blueprint (Well-Worn)",
    "M4A1-S | Flashback (Field-Tested)",
    "USP-S | Whiteout (Factory New)",
]
