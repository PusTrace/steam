from .confirmation import (
    get_confirmations,
    accept_all_confirmations,
)
import core.models as obj
import requests


class ConfirmationService:
    """
    Responsibilities:
        - confirm all items
        - show current pending confirmations
    """

    def __init__(self, session: requests.Session, mafile: obj.Secrets):
        self.session = session
        self.mafile = mafile

    def get_conf(self):
        confirmations = get_confirmations(
            session=self.session,
            identity_secret=self.mafile.identity_secret,
            offset=0,
        )
        return confirmations

    def accept_all(self):
        resp = accept_all_confirmations(
            session=self.session,
            identity_secret=self.mafile.identity_secret,
        )
        return resp
