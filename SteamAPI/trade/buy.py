from urllib.parse import urlencode


def buy_skin_by_listing_id(session, listing_id, price, price_without_fee, sessionid):
    """Покупка предмета по listing_id."""
    fee = round((price - price_without_fee) * 100)
    total = round(price * 100)
    subtotal = round(price_without_fee * 100)

    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Referer": "https://steamcommunity.com/market/",
        "Origin": "https://steamcommunity.com",
        "User-Agent": "Mozilla/5.0",
    }

    data = {
        "sessionid": sessionid,
        "currency": "1",
        "subtotal": subtotal,
        "fee": fee,
        "total": total,
        "quantity": 1,
    }

    url = f"https://steamcommunity.com/market/buylisting/{listing_id}"
    resp = session.post(url, data=urlencode(data), headers=headers)
    print("📦 Ответ покупки:", resp.status_code, resp.text[:500])
    if resp.status_code == 406 and "need_confirmation" in resp.text:
        print("⚠️ Требуется подтверждение в мобильном приложении")
    elif "success" in resp.text:
        print("✅ Покупка успешна")
    else:
        print("❌ Ошибка покупки")
