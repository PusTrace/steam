import json
import os
import sys
import numpy as np
from datetime import datetime, timedelta

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
from utils.utils import save_data

def calculate_approx_price_range(recent_prices):
    """
    Вычисляет приближённые минимальную и максимальную цены за период,
    начиная с даты последней записи минус 3 дня.
    Для вычисления берутся три наименьших и три наибольших цены из отфильтрованных данных.
    """
    if not recent_prices:
        return None

    # Определяем дату последней записи
    last_record = recent_prices[-1]
    try:
        parts = last_record[0].split()
        if len(parts) < 4:
            return None
        hour = parts[3].replace(":", "")
        date_str = " ".join(parts[:3] + [hour])
        last_date = datetime.strptime(date_str, "%b %d %Y %H")
    except Exception as e:
        print(f"Ошибка при обработке последней записи {last_record}: {e}")
        return None

    # Вычисляем пороговую дату: last_date - 3 дня
    threshold_date = last_date - timedelta(days=3)
    filtered_prices = []

    for record in recent_prices:
        try:
            parts = record[0].split()
            if len(parts) < 4:
                continue
            hour = parts[3].replace(":", "")
            date_str = " ".join(parts[:3] + [hour])
            entry_date = datetime.strptime(date_str, "%b %d %Y %H")
            if entry_date >= threshold_date:
                filtered_prices.append(float(record[1]))
        except Exception as e:
            print(f"Ошибка при обработке записи {record}: {e}")
            continue

    if not filtered_prices:
        return None

    # Теперь сортируем цены по значению (от минимальной к максимальной)
    sorted_prices = sorted(filtered_prices)
    
    # Берём три наименьших и три наибольших цены
    if len(sorted_prices) < 3:
        min_prices = sorted_prices
        max_prices = sorted_prices
    else:
        min_prices = sorted_prices[:3]
        max_prices = sorted_prices[-3:]
    
    approx_min = sum(min_prices) / len(min_prices)
    approx_max = sum(max_prices) / len(max_prices)
    
    return {"approx_min": approx_min, "approx_max": approx_max}

def analyze_trends(input_filename, output_filename):
    """
    Анализирует тренды цен, определяет плавный рост и отбрасывает волатильные предметы.
    Дополнительно вычисляет приближённые минимальную и максимальную цены за период,
    начиная с даты (дата последней записи - 3 дня).
    """
    with open(input_filename, 'r', encoding='utf-8') as f:
        skins = json.load(f)

    filtered_data = {}

    for skin_name, item in skins.items():
        appearance_date = item.get("appearance_date")
        recent_prices = item.get("recent_prices", [])
        
        if len(recent_prices) < 3:
            continue  # Недостаточно данных для анализа

        try:
            # Преобразуем цены в float для вычисления тренда
            prices = [float(record[1]) for record in recent_prices]
        except Exception as e:
            print(f"Ошибка при преобразовании цены для {skin_name}: {e}")
            continue
        
        # Вычисляем процентные изменения между соседними записями
        percent_changes = [
            (prices[i] - prices[i - 1]) / prices[i - 1] * 100 
            for i in range(1, len(prices))
        ]
        avg_trend = np.mean(percent_changes)
        volatility = np.std(percent_changes)
        if volatility > 300:
            volatility = 300
        volatility = volatility / 3

        # Вычисляем приближённые минимальную и максимальную цены за период (последняя дата - 3 дня)
        approx_range = calculate_approx_price_range(recent_prices)

        if avg_trend > 0 and volatility > 0:
            filtered_data[skin_name] = {
                "appearance_date": appearance_date,
                "average_trend_percent": f"{avg_trend:.2f}%",
                "volatility_percent": f"{volatility:.2f}%",
                "approx_min": f"{approx_range['approx_min']:.2f}" if approx_range else None,
                "approx_max": f"{approx_range['approx_max']:.2f}" if approx_range else None
            }

    save_data(filtered_data, output_filename)

if __name__ == "__main__":
    analyze_trends(
        "/home/pustrace/programming/trade/steam/database/price_history.json",
        "/home/pustrace/programming/trade/steam/database/perfect.json"
    )
