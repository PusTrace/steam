from __future__ import annotations

import hmac
import struct
from base64 import b64decode, b64encode
from hashlib import sha1
from time import time


def generate_one_time_code(
    shared_secret: str,
    timestamp: int | None = None,
) -> str:
    if timestamp is None:
        timestamp = int(time())

    time_buffer = struct.pack(">Q", timestamp // 30)

    digest = hmac.new(
        b64decode(shared_secret),
        time_buffer,
        digestmod=sha1,
    ).digest()

    offset = digest[19] & 0xF

    full_code = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF

    chars = "23456789BCDFGHJKMNPQRTVWXY"

    code = ""

    for _ in range(5):
        full_code, index = divmod(full_code, len(chars))
        code += chars[index]

    return code


def generate_confirmation_key(
    identity_secret: str, tag: str, timestamp: int = int(time())
) -> bytes:
    buffer = struct.pack(">Q", timestamp) + tag.encode("ascii")
    return b64encode(
        hmac.new(b64decode(identity_secret), buffer, digestmod=sha1).digest()
    )
