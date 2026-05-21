import sys
from pathlib import Path
import logging

# добавляем корень проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from SteamAPI import SteamAPI
import core.models as obj
from core.logging_config import setup_logging

setup_logging(module_name="2fa", level=logging.DEBUG)
api = SteamAPI(obj.load_secrets(), obj.load_config())
code = api.auth.create_auth_code()
print(f"2fa: {code}")
