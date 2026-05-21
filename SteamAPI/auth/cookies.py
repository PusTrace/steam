import json
import os
import time
import requests
from pathlib import Path


def save_cookies(cookies_dict, path: str = "config/cookies.json"):
    Path(path).write_text(json.dumps(cookies_dict, indent=2), encoding="utf-8")


def read_cookies(path: str = "config/cookies.json"):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def is_fresh(file: str = "config/cookies.json", cookies_max_age: int = 31536000):
    if not os.path.exists(file):
        return False
    return time.time() - os.path.getmtime(file) < cookies_max_age


def load_cookies(session: requests.Session, path: str = "config/cookies.json"):
    import json
    from pathlib import Path

    data = json.loads(Path(path).read_text(encoding="utf-8"))

    jar = requests.cookies.RequestsCookieJar()

    for k, v in data.items():
        jar.set(k, v)

    session.cookies.update(jar)
    return session
