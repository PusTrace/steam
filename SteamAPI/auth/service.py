from typing import Dict
import requests
import logging

from .guard import generate_one_time_code
from .login import LoginExecutor
from core.models import SteamUrl

log = logging.getLogger("SteamAPI.auth")


class AuthService:
    """
    Steam authentication orchestration service.

    Responsibilities:
        - login
        - generate Steam Guard auth codes
    """

    DEFAULT_DOMAIN = "steamcommunity.com"

    def __init__(self, secrets) -> None:
        self.headers: Dict[str, str] = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/118.0.5993.118 Safari/537.36"
            ),
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": f"{SteamUrl.COMMUNITY_URL}/",
            "Origin": SteamUrl.COMMUNITY_URL,
        }

        self.secrets = secrets
        self._session = requests.Session()
        self.login_executed = False

    def login(self) -> requests.Session:
        """
        Create authenticated requests session.
        """
        # TODO: restore cookies
        self.session = LoginExecutor(
            self.secrets.account_name,
            self.secrets.password,
            self.secrets.shared_secret,
            self._session,
        ).login()

        return self.session

    def create_auth_code(self) -> str:
        """
        Generate current Steam Guard auth code.
        """

        if not self.secrets.shared_secret:
            raise ValueError("SHARED_SECRET is not set")

        return generate_one_time_code(self.secrets.shared_secret)
