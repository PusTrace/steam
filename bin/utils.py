import urllib.parse
def generate_market_url(skin_name):
    """Генерирует URL для скина на маркете Steam."""
    encoded_name = urllib.parse.quote(skin_name)
    url = f"https://steamcommunity.com/market/listings/730/{encoded_name}"
    return url

from datetime import datetime, timezone

def normalize_date(raw_date):
    """Преобразует дату (строку ISO или datetime) в UTC-aware datetime, округлённый до часа."""
    if isinstance(raw_date, str):
        try:
            dt = datetime.fromisoformat(raw_date.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError(f"Не удалось распарсить дату: {raw_date}")
    elif isinstance(raw_date, datetime):
        dt = raw_date
    else:
        raise TypeError(f"Ожидалась строка или datetime, а получено: {type(raw_date)}")

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    # Округляем до часа
    dt = dt.replace(minute=0, second=0, microsecond=0)
    return dt
