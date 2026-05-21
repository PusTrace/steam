import sys
from pathlib import Path
import os

from dotenv import load_dotenv
import pytest

from core.db import PostgreSQLDB

sys.path.insert(0, str(Path(__file__).parent.parent))

from core import objects as obj
from SteamAPI import SteamAPI
from SteamAPI import SteamAPI

# ─────────────────────────────────────────────────────────────────── #
#   фикстуры                                            #
# ─────────────────────────────────────────────────────────────────── #


@pytest.fixture(scope="session")
def config() -> obj.Config:
    return obj.load_config()


@pytest.fixture(scope="session")
def mafile() -> obj.Mafile:
    return obj.load_mafile()


@pytest.fixture(scope="session")
def api(mafile, config):
    api = SteamAPI(mafile=mafile, config=config)
    return api


@pytest.fixture(scope="session")
def db():
    load_dotenv()
    db = PostgreSQLDB(host=os.getenv("DB_HOST"), password=os.getenv("DEFAULT_PASSWORD"))
    return db


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
