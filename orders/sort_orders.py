import json

# Загрузка данных из файлов
with open("/home/pustrace/programming/trade/steam/database/orders.json", 'r', encoding='utf-8') as f:
    orders_data = json.load(f)
with open("/home/pustrace/programming/trade/steam/database/perfect.json", 'r', encoding='utf-8') as f:
    perfect_data = json.load(f)

filtered_perfect_data = {}

for skin, skin_info in perfect_data.items():
    try:
        median_price = skin_info["median_price"]
        lowest_price = skin_info["lowest_price"]
        volume = skin_info["volume"]
    except Exception as e:
        print(f"Ошибка преобразования значений для {skin}: {e}")
        continue

    # Вычисляем целевую цену: 75% и 87% от median_price (если есть) или от lowest_price
    target_price = median_price * 0.75 if median_price is not None else lowest_price * 0.75
    target_price_87 = median_price * 0.87 if median_price is not None else lowest_price * 0.87

    # Получаем данные по ордерам
    skin_orders = orders_data.get(skin, {})
    buy_order_graph = skin_orders.get("buy_order_graph", [])

    # Предполагается, что buy_order_graph отсортирован по цене в порядке убывания.
    for i in range(len(buy_order_graph) - 1):
        price_high = buy_order_graph[i][0]
        price_low = buy_order_graph[i+1][0]
        if price_high > target_price_87 > price_low:
            skin_info["order_info_87"] = buy_order_graph[i+1][1]
        if price_high > target_price > price_low:
            skin_info["order_info"] = buy_order_graph[i+1][1]

    # Если массив не пустой, сохраняем последний элемент массива
    if buy_order_graph:
        skin_info["order_info_last"] = buy_order_graph[-1][1]

    filtered_perfect_data[skin] = skin_info

# Сохраняем обновлённые данные с корректным выводом Unicode символов
with open("/home/pustrace/programming/trade/steam/database/perfect.json", "w", encoding="utf-8") as f:
    json.dump(filtered_perfect_data, f, indent=4, ensure_ascii=False)

print("Обработка завершена!")
