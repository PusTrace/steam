import requests, time
from urllib.parse import unquote

from core.steam.crypt import generate_confirmation_key, get_device_id, get_time_offset, steam_time

STEAM_COMMUNITY_URL = "https://steamcommunity.com"
_used_conf_times = []

def steam_request(
    session,
    url: str,
    steamid: str,
    key: str,
    timestamp: int,
    tag: str,
    params: dict = None,
    json_mode: bool = False
):
    """
    session – requests.Session()
    url – 'getlist', 'details', 'confirm', 'multiajaxop'
    steamid – SteamID64
    key – confirmation key
    timestamp – unix time
    tag – 'conf', 'allow', 'cancel', 'details'
    params – дополнительные параметры (cid, ck и т.п.)
    json_mode – если нужно вернуть JSON (аналог req.json = true)
    """

    if not steamid:
        raise Exception("Must be logged in before trying to do anything with confirmations")

    # === 1. БАЗОВЫЕ ПАРАМЕТРЫ ===
    params = params or {}
    params['p'] = get_device_id(steamid)
    params['a'] = steamid
    params['k'] = key
    params['t'] = timestamp
    params['m'] = 'react'
    params['tag'] = tag

    # === 2. Сборка URL ===
    req_url = f"https://steamcommunity.com/mobileconf/{url}"

    # === 3. Выбор метода ===
    # multiajaxop → POST
    method = "POST" if url == "multiajaxop" else "GET"

    # === 4. Выполнение запроса ===
    try:

        if method == "GET":
            resp = session.get(
                req_url,
                params=params,
                timeout=(5, 10)
            )
        else:
            resp = session.post(
                req_url,
                data=params,
                timeout=(5, 10)
            )


    except requests.Timeout:
        print("[STEAM_REQ] TIMEOUT")
        return {"success": False, "error": "timeout"}

    except requests.RequestException as e:
        print(f"[STEAM_REQ] network error: {e}")
        return {"success": False, "error": str(e)}

    # === 5. Возврат body ===
    if json_mode:
        try:
            data = resp.json()
            return data
        except Exception as e:
            print(f"[STEAM_REQ] invalid json: {resp.text[:200]}")
            return {"success": False, "error": "invalid_json"}


    return resp


def get_confirmations(session, cookies, identity_secret, offset):
    """Получаем список всех подтверждений (как Node.js getConfirmations)"""
    steam_login_secure = cookies.get("steamLoginSecure")
    steam_login_secure = unquote(steam_login_secure)
    steamid = steam_login_secure.split("|")[0] if steam_login_secure else None
    if not steamid:
        raise Exception("SteamID не найден в cookies")

    timestamp = steam_time(offset)
    key = generate_confirmation_key(identity_secret, timestamp, "conf")

    body = steam_request(session, 'getlist', steamid, key, timestamp, 'conf', json_mode=True)

    if not body.get('success', False):
        raise Exception(body.get('message') or body.get('detail') or "Не удалось получить список подтверждений")

    confirmations = []
    for conf in body.get('conf', []):
        confirmations.append({
            'id': conf.get('id'),
            'type': conf.get('type'),
            'creator': conf.get('creator_id'),
            'key': conf.get('nonce'),
            'title': f"{conf.get('type_name', 'Confirm')} - {conf.get('headline', '')}",
            'sending': (conf.get('summary') or [])[0] if conf.get('summary') else '',
            'receiving': (conf.get('summary') or [])[1] if conf.get('summary') and conf.get('type') == 2 else '',
            'time': conf.get('creation_time')
        })

    return confirmations

def steam_confirm(session, cookies, steamid, identity_secret, conf_id, conf_key):
    """Отправляет подтверждение по exact API Steam Mobile"""

    timestamp = int(time.time())

    params = {
        "op": "allow",
        "cid": conf_id,
        "ck": conf_key,
        "p": get_device_id(steamid),
        "a": steamid,
        "k": generate_confirmation_key(identity_secret, timestamp, "allow"),
        "t": timestamp,
        "m": "react",
        "tag": "allow"
    }

    url = "https://steamcommunity.com/mobileconf/ajaxop"

    resp = session.get(url, params=params, cookies=cookies)

    try:
        return resp.json()
    except:
        print("RAW:", resp.text)
        return None

def accept_all_confirmations(session, cookies, identity_secret):
    """
    Принимает все подтверждения из списка
    """

    # Получаем список подтверждений
    confirmations = get_confirmations(session, cookies, identity_secret, 0)

    if not confirmations:
        return {"success": True, "accepted": [], "message": "Нет подтверждений"}

    steamid = unquote(cookies.get("steamLoginSecure")).split("|")[0]

    results = []

    for conf in confirmations:
        conf_id = conf["id"]
        conf_key = conf["key"]
        time.sleep(1)
        timestamp = int(time.time())
        key = generate_confirmation_key(identity_secret, timestamp, "allow")
        params = {
            "op": "allow",
            "cid": conf_id,
            "ck": conf_key
        }
        url = "ajaxop"  # если одиночное подтверждение

        resp = steam_request(
            session=session,
            url=url,
            steamid=steamid,
            key=key,
            timestamp=timestamp,
            tag="allow",
            params=params,
            json_mode=True
        )

        results.append({
            "id": conf_id,
            "response": resp
        })

    return results


def accept_confirmation_for_order(session, cookies, identity_secret, object_id):
    global _used_conf_times

    # steamLoginSecure → steamID64
    steamid = unquote(cookies["steamLoginSecure"]).split("|")[0]

    # 1. Получаем server time offset
    offset, latency = get_time_offset()

    # 2. Получаем список подтверждений с tag=list
    confs = get_confirmations(session, cookies, identity_secret, offset)

    target = None
    for c in confs:
        if str(c["creator"]) == str(object_id):
            target = c
            break

    if not target:
        return {"success": False, "error": f"confirmation for {object_id} not found"}

    # 3. Генерация уникального timestamp (как node)
    local_offset = 0
    while True:
        timestamp = steam_time() + offset + local_offset
        if timestamp not in _used_conf_times:
            break
        local_offset += 1

    # сохранить в историю
    _used_conf_times.append(timestamp)
    if len(_used_conf_times) > 60:
        _used_conf_times = _used_conf_times[-60:]

    # 4. Генерация KEY для accept
    key = generate_confirmation_key(identity_secret, timestamp, "accept")

    params = {
        "op": "accept",
        "cid": target["id"],
        "ck": target["key"]
    }

    result = steam_request(
        session=session,
        url="ajaxop",
        steamid=steamid,
        key=key,
        timestamp=timestamp,
        tag="accept",
        params=params,
        json_mode=True
    )

    # Node ожидает {success: true}
    if result and result.get("success"):
        return {"success": True}

    return {"success": False, "response": result}