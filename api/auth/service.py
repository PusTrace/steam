import time

from .cookies import ensure_cookies, get_identity_secret
from .crypt import generate_auth_code, get_device_id, get_time_offset


class AuthService:
    """
    AuthService = orchestration layer for Steam identity/auth state.

    Responsibilities:
    - manage cookies lifecycle
    - maintain session state
    - provide steam identity info
    - ensure system is authenticated for API usage
    """

    def __init__(self, session, config=None):
        self.session = session
        self.config = config

        self._cookies = None
        self._steamid = None
        self._identity_secret = None
        self._time_offset = 0
        self._ready = False

    # --------------------------------------------------
    # CORE
    # --------------------------------------------------

    def ensure(self, reload: bool = False) -> bool:
        """
        Brings auth system into valid state.
        This is the main entry point.
        """

        self._cookies = ensure_cookies(reload=reload)
        self._apply_cookies()

        self._steamid = self._extract_steamid()
        self._identity_secret = get_identity_secret()

        self._time_offset, _latency = get_time_offset()

        self._ready = self._steamid is not None and self._cookies is not None

        return self._ready

    # --------------------------------------------------
    # STATE
    # --------------------------------------------------

    def is_ready(self) -> bool:
        return self._ready

    def is_logged_in(self) -> bool:
        return self._steamid is not None

    def steamid(self) -> str | None:
        return self._steamid

    def session(self):
        return self.session

    # --------------------------------------------------
    # 2FA / SECURITY HELPERS (optional exposure)
    # --------------------------------------------------

    def get_2fa_code(self) -> str | None:
        if not self._identity_secret:
            return None
        return generate_auth_code(self._identity_secret, self._time_offset)

    def get_device_id(self) -> str | None:
        if not self._steamid:
            return None
        return get_device_id(self._steamid)

    # --------------------------------------------------
    # INTERNALS
    # --------------------------------------------------

    def _apply_cookies(self):
        """
        Inject parsed cookies into requests.Session
        """
        if not self._cookies:
            return

        for domain, cookies in self._cookies.items():
            for k, v in cookies.items():
                self.session.cookies.set(k, v)

    def _extract_steamid(self) -> str | None:
        """
        SteamID64 is stored inside steamLoginSecure cookie
        format: steamid|token
        """
        cookie = self.session.cookies.get("steamLoginSecure")
        if not cookie:
            return None

        return cookie.split("|")[0]
