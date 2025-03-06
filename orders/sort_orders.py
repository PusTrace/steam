import json
import sys
import os

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
from utils.utils import save_data

# Загрузка данных из файлов
with open("/home/pustrace/programming/trade/steam/database/orders.json", 'r', encoding='utf-8') as f:
    orders_data = json.load(f)
with open("/home/pustrace/programming/trade/steam/database/perfect.json", 'r', encoding='utf-8') as f:
    perfect_data = json.load(f)

filtered_perfect_data = {}

for skin, skin_info in perfect_data.items():
    # Извлекаем цены и объем
    median_price = skin_info.get("median_price")
    lowest_price = skin_info.get("lowest_price")
    volume = skin_info.get("volume")
    
    try:
        if median_price is not None:
            median_price = float(median_price)
        if lowest_price is not None:
            lowest_price = float(lowest_price)
        volume = float(volume)
    except Exception as e:
        print(f"Ошибка преобразования значений для {skin}: {e}")
        continue

    # Вычисляем целевую цену: 75% от median_price (если есть) или от lowest_price
    if median_price is not None:
        target_price = median_price * 0.75
    else:
        target_price = lowest_price * 0.75

    # Получаем данные по ордерам
    skin_orders = orders_data.get(skin, {})
    buy_order_graph = skin_orders.get("buy_order_graph", [])
    
    # Предполагается, что buy_order_graph отсортирован по цене в порядке убывания.
    found_order = False
    for i in range(len(buy_order_graph) - 1):
        price_high = buy_order_graph[i][0]
        price_low = buy_order_graph[i+1][0]
        # Если целевая цена лежит между ценой текущего и следующего ордера:
        if price_high > target_price > price_low:
            # Добавляем информацию о найденном ордере в skin_info:
            if "order_info" not in skin_info:
                skin_info["order_info"] = buy_order_graph[i+1][1]
            found_order = True
            break

    # Если ордер не найден, можно по желанию оставить skin_info без order_info
    filtered_perfect_data[skin] = skin_info

# Сохраняем обновлённые данные (например, в новый файл)
with open("/home/pustrace/programming/trade/steam/database/perfect.json", "w", encoding="utf-8") as f:
    json.dump(filtered_perfect_data, f, indent=4)

print("Обработка завершена!")
