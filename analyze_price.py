from bin.get_history import get_history
from datetime import datetime, timedelta, timezone

def analyze_price(history):
    now = datetime.now(timezone.utc)
    one_week_ago = now - timedelta(days=7)

    total_price = 0.0
    volume = 0
    count = 0

    last_week_records = []

    for record in history:
        dt = datetime.fromisoformat(record[0].replace('Z', '+00:00'))
        if dt >= one_week_ago:
            _price = record[1]
            _volume = record[2]
            total_price += _price
            volume += _volume
            count += 1
            last_week_records.append(record)

    if count == 0:
        print("Нет данных за последнюю неделю.")
        return

    price = total_price / count

    # Сортировка по цене
    sorted_by_price = sorted(last_week_records, key=lambda x: x[1])

    # 3 самых дешёвых
    cheapest = sorted_by_price[:3]
    approx_min = sum([r[1] for r in cheapest]) / len(cheapest)

    # 3 самых дорогих
    most_expensive = sorted_by_price[-3:]
    approx_max = sum([r[1] for r in most_expensive]) / len(most_expensive)
    
    return price, volume, approx_max, approx_min

def test():
    skin_name = "SG 553 | Waves Perforated (Field-Tested)"
    history = get_history(skin_name)
    price, volume, approx_max, approx_min = analyze_price(history)
    print(f"Средняя цена: {price:.2f} RUB")
    print(f"Объём: {volume}")
    print(f"Приблизительная максимальная цена: {approx_max:.2f} RUB")
    print(f"Приблизительная минимальная цена: {approx_min:.2f} RUB")

if __name__ == "__main__":
    test()
