import base64, hashlib, hmac, os, requests
from datetime import time
import time


# ------------------------------------------------------
# 1. Время 
# ------------------------------------------------------
def steam_time(offset: int = 0) -> int:
    return int(time.time()) + offset


# ------------------------------------------------------
# 2. Преобразование секрета 
# ------------------------------------------------------
def bufferize_secret(secret: str | bytes) -> bytes:
    if isinstance(secret, bytes):
        return secret

    if isinstance(secret, str):
        # hex?
        if len(secret) == 40 and all(c in "0123456789abcdefABCDEF" for c in secret):
            return bytes.fromhex(secret)
        else:
            # считаем что base64
            return base64.b64decode(secret)

    raise ValueError("Invalid secret format")


# ------------------------------------------------------
# 3. Генерация TOTP-кода Steam 
# ------------------------------------------------------
def generate_auth_code(secret: str | bytes, time_offset: int = 0) -> str:
    """
    where secret = shared_secret
    """
    secret = bufferize_secret(secret)
    current_time = steam_time(time_offset)

    # Steam считает таймстеп = time // 30
    timestep = int(current_time / 30)

    # 8-байтовый big-endian buffer
    buffer = timestep.to_bytes(8, "big")

    # HMAC-SHA1
    hmac_hash = hmac.new(secret, buffer, hashlib.sha1).digest()

    # dynamic truncation
    start = hmac_hash[19] & 0x0F
    code_int = int.from_bytes(hmac_hash[start:start+4], "big") & 0x7FFFFFFF

    chars = "23456789BCDFGHJKMNPQRTVWXY"
    result = ""

    for _ in range(5):
        result += chars[code_int % len(chars)]
        code_int //= len(chars)

    return result


# ------------------------------------------------------
# 4. Confirmation key 
# ------------------------------------------------------
def generate_confirmation_key(identity_secret: str | bytes, timestamp: int, tag: str) -> str:
    identity_secret = bufferize_secret(identity_secret)

    # Соответствует node.js: 8 байт времени + tag
    data = timestamp.to_bytes(8, "big") + tag.encode()

    hmac_hash = hmac.new(identity_secret, data, hashlib.sha1).digest()
    return base64.b64encode(hmac_hash).decode()


# ------------------------------------------------------
# 5. Получение time offset от Steam 
# ------------------------------------------------------
def get_time_offset() -> tuple[int, int]:
    start = time.time()

    r = requests.post(
        "https://api.steampowered.com/ITwoFactorService/QueryTime/v1/",
        data=b""
    )

    if r.status_code != 200:
        raise RuntimeError(f"Steam HTTP error {r.status_code}")

    data = r.json().get("response")

    if not data or "server_time" not in data:
        raise RuntimeError("Malformed Steam response")

    latency_ms = int((time.time() - start) * 1000)
    offset = int(data["server_time"]) - steam_time()

    return offset, latency_ms


# ------------------------------------------------------
# 6. Device ID 
# ------------------------------------------------------
def get_device_id(steamid: str) -> str:
    salt = os.environ.get("STEAM_TOTP_SALT", "")
    raw = (steamid + salt).encode()

    digest = hashlib.sha1(raw).hexdigest()

    # формат UUID: 8-4-4-4-12
    formatted = (
        f"{digest[0:8]}-{digest[8:12]}-{digest[12:16]}-"
        f"{digest[16:20]}-{digest[20:32]}"
    )

    return f"android:{formatted}"
