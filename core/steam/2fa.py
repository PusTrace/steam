import base64, struct, hashlib, hmac
import time
from dotenv import load_dotenv
import os

def generate_auth_code(shared_secret: str) -> str:
    """Создает 2FA-код для Steam."""
    time_buffer = struct.pack(">Q", int(time.time()) // 30)
    secret = base64.b64decode(shared_secret)
    hmac_hash = hmac.new(secret, time_buffer, hashlib.sha1).digest()
    start = hmac_hash[19] & 0xF
    full_code = struct.unpack(">I", hmac_hash[start:start + 4])[0] & 0x7FFFFFFF
    chars = '23456789BCDFGHJKMNPQRTVWXY'
    code = ''
    for _ in range(5):
        code += chars[full_code % len(chars)]
        full_code //= len(chars)
    return code

if __name__ == "__main__":
    load_dotenv()
    shared_secret = os.getenv("SHARED_SECRET")
    print("Generated 2FA Code:", generate_auth_code(shared_secret))