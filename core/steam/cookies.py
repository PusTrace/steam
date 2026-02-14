import json, os, subprocess, sys
from datetime import time
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]  # это steam/

MA_FILE = BASE_DIR / "config/sda.json"
COOKIES_FILE = BASE_DIR / "config/cookies.json"
NODE_DIR = BASE_DIR / "core/node"

COOKIE_MAX_AGE = 31536000  # требуемая "свежесть", например 1 год

def read_cookies():
    try:
        with open(COOKIES_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return None

def is_fresh():
    if not os.path.exists(COOKIES_FILE):
        print("[is_fresh] cookies file does not exist")
        return False
    return time.time() - os.path.getmtime(COOKIES_FILE) < COOKIE_MAX_AGE

def parse_cookie_array(cookies_array):
    cookies_by_domain = {}
    for item in cookies_array:
        kv, *attrs = item.split(";")
        if "=" in kv:
            k, v = kv.split("=", 1)
            domain = None
            for attr in attrs:
                attr = attr.strip()
                if attr.lower().startswith("domain="):
                    domain = attr.split("=", 1)[1].lower()
            if domain:
                if domain not in cookies_by_domain:
                    cookies_by_domain[domain] = {}
                cookies_by_domain[domain][k] = v
    return cookies_by_domain


def ensure_cookies(reload: bool = False):
    if not reload:
        if is_fresh():
            payload = read_cookies()
            cookies = parse_cookie_array(payload)
            return cookies

    # иначе запускаем Node
    print("[ensure_cookies] cookies missing or expired, running Node...")
    

    subprocess.run(
        ["node", "core/node/get-cookies.js"],
        cwd=BASE_DIR,   # steam
        check=True
    )


    time.sleep(10)
    # ждём и читаем снова
    payload = read_cookies()
    cookies = parse_cookie_array(payload)
    return cookies

def get_identity_secret():
    try:
        with open(MA_FILE, "r") as f:
            data = json.load(f)
        return data.get("identity_secret")
    except Exception:
        return None 
    
    
if __name__ == "__main__":
    print("force update cookies")
    ensure_cookies(True)