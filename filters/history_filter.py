import json
import json
import os
import sys
import json
import numpy as np
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
from utils.utils import save_data

def analyze_trends(input_filename, output_filename):
    """Анализирует тренды цен, определяет плавный рост и отбрасывает волатильные предметы."""
    
    with open(input_filename, 'r', encoding='utf-8') as f:
        skins = json.load(f)

    filtered_data = {}

    for skin_name, item in skins.items():
        appearance_date = item["appearance_date"]
        recent_prices = [record[1] for record in item["recent_prices"]]

        if len(recent_prices) < 3:
            continue  # Слишком мало данных

        # 1. Вычисляем процентное изменение цены между соседними значениями
        percent_changes = [(recent_prices[i] - recent_prices[i - 1]) / recent_prices[i - 1] * 100 
                           for i in range(1, len(recent_prices))]

        # 2. Вычисляем средний тренд роста
        avg_trend = np.mean(percent_changes)  # Средний рост в %

        # 3. Вычисляем стандартное отклонение (волатильность)
        volatility = np.std(percent_changes)  # Насколько сильно скачут цены
        if volatility > 300:
            volatility = 300
        volatility = volatility / 3
        # 4. Оставляем предметы, если:
        #    - Средний рост положительный
        #    - Волатильность не слишком большая
        if avg_trend > 0 and volatility > 0:  # Можно подстроить порог
            filtered_data[skin_name] = {
                "appearance_date": appearance_date,
                "average_trend_percent": f"{avg_trend:.2f}%",
                "volatility_percent": f"{volatility:.2f}%"
            }

    # Запись результата в JSON
    save_data(filtered_data, output_filename)
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(filtered_data, f, ensure_ascii=False, indent=4)

# Вызов функции
if __name__ == "__main__":
    analyze_trends("steam/database/price_history.json", "steam/database/perfect.json")
