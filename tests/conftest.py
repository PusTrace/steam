# tests/conftest.py

import pytest
from dotenv import load_dotenv

from core.init import init_environment
import core.objects as obj


@pytest.fixture(scope="session")
def environment():

    load_dotenv()

    session, _, db = init_environment()

    return session, db


@pytest.fixture
def config():

    return obj.load_config()
