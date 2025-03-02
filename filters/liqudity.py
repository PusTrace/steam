import json

# Открываем JSON-файл
with open("main/database/perfect.json", "r", encoding="utf-8") as file:
    data = json.load(file)

# Обрабатываем данные
for skin, values in data.items():
    volume = int(values["volume"].replace(",", ""))  # Убираем запятые, если есть
    all_orders = int(values["all_orders"])  
    liquidity = volume / (all_orders + 1)  # Рассчитываем ликвидность
    data[skin]["liquidity"] = liquidity  # Добавляем в словарь

# Сохраняем обновлённый JSON-файл
with open("main/database/perfect.json", "w", encoding="utf-8") as file:
    json.dump(data, file, indent=4, ensure_ascii=False)

print("Ликвидность добавлена в файл.")
