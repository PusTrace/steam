import json

with open("/home/pustrace/programming/trade/steam/database/perfect.json", 'r', encoding='utf-8') as f:
    perfect_data = json.load(f)

filtered_perfect_data = {}

def clean_price(price_str):
    if price_str is None:
        return None
    return float(price_str.replace("₸", "").replace(",", ".").replace(" ", "").strip())

def clean_percent(volume_str):
    if volume_str is None:
        return None
    return float(volume_str.replace("%", "").strip())

def clean_volume(volume_str):
    if volume_str is None:
        return None
    return int(volume_str.replace(",", "").strip())

for skin, skin_info in perfect_data.items():
    try:
        median_price = clean_price(skin_info.get("median_price"))
        lowest_price = clean_price(skin_info.get("lowest_price"))
        volume = clean_volume(skin_info.get("volume"))
        approx_min = clean_price(skin_info.get("approx_min"))
        approx_max = clean_price(skin_info.get("approx_max"))
        average_trend_percent = clean_percent(skin_info.get("average_trend_percent"))
        volatility_percent = clean_percent(skin_info.get("volatility_percent"))
    except Exception as e:
        print(f"Ошибка преобразования значений для {skin}: {e}")
        continue

    # Обновляем словарь с числовыми значениями
    skin_info["median_price"] = median_price
    skin_info["lowest_price"] = lowest_price
    skin_info["volume"] = volume
    skin_info["approx_min"] = approx_min
    skin_info["approx_max"] = approx_max
    skin_info["average_trend_percent"] = average_trend_percent
    skin_info["volatility_percent"] = volatility_percent
    
    filtered_perfect_data[skin] = skin_info
    
# Сохраняем обновлённые данные (например, в новый файл) с корректным выводом Unicode символов
with open("/home/pustrace/programming/trade/steam/database/perfect.json", "w", encoding="utf-8") as f:
    json.dump(filtered_perfect_data, f, indent=4, ensure_ascii=False)