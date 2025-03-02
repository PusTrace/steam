import pandas as pd
import json
from datetime import datetime

def parse_date(date_str):
    """Парсит дату из строки вида 'Feb 18 2016 01: +0'."""
    date_format = "%b %d %Y"
    return datetime.strptime(" ".join(date_str.split()[:3]), date_format)

# Загрузка исходного JSON из файла
with open("/home/pustrace/programming/steam_parser/main/database/unsorted_price_history.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Определяем период анализа
start_window = datetime(2025, 1, 14)
end_window = datetime(2025, 2, 14)

# Создаём DataFrame
records = []
first_sale_dates = {}
for skin, details in data.items():
    if details.get("prices"):
        first_sale_dates[skin] = parse_date(details["prices"][0][0]).strftime("%Y-%m-%d")
    for rec in details.get("prices", []):
        rec_date = parse_date(rec[0])
        if start_window <= rec_date <= end_window:
            records.append([skin, rec_date, float(rec[1]), int(rec[2])])

df = pd.DataFrame(records, columns=['skin', 'timestamp', 'price', 'volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'])
df.sort_values(by=['skin', 'timestamp'], inplace=True)

def calculate_stability_index(df, first_sale_dates, baseline=10):
    results = {}
    
    for skin, group in df.groupby('skin'):
        group = group.copy()
        group['prev_price'] = group['price'].shift(1)
        group['price_change'] = (group['price'] - group['prev_price']) / group['prev_price'] * 100
        
        # Фильтрация аномалий (рост более чем на 300% за раз)
        group = group[~(group['price_change'] > 100)]
        
        if group.empty:
            continue
        
        # Анализ изменений внутри дня
        group['date'] = group['timestamp'].dt.date
        intraday_changes = group.groupby(['date', 'skin'])['price_change'].sum()
        volatility = intraday_changes.abs().mean()
        
        monthly_change = (group['price'].iloc[-1] - group['price'].iloc[0]) / group['price'].iloc[0] * 100
        
        stability_index = baseline + monthly_change - volatility
        monthly_volume = int(group['volume'].sum())
        
        results[skin] = {
            "monthly_percentage_change": round(float(monthly_change), 2),
            "daily_fluctuation_indicator": round(float(stability_index), 2),
            "monthly_volume": monthly_volume,
            "first_sale_date": first_sale_dates.get(skin, "Unknown")
        }
    
    return results

stability_results = calculate_stability_index(df, first_sale_dates)

# Сохранение результатов в JSON
output_path = "/home/pustrace/programming/steam_parser/main/database/analysis_result.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(stability_results, f, indent=4, ensure_ascii=False)

print("Анализ завершён. Результаты сохранены в", output_path)
