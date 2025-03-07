import json
import math
from datetime import datetime

def calculate_weight_number_of_items(lowest_price,
                                    median_price,
                                    order_info_87,
                                    order_info_last,
                                    volatility_percent,
                                    appearance_date):
    weight_of_orders = round(((order_info_last / order_info_87) * 100), 2)
    
    price = median_price if median_price is not None else lowest_price
    # Коэффициент масштабирования для обратной экспоненты (можно подбирать эмпирически)
    scale = 300.0
    price_weight = math.exp(-price / scale) * 100
    
    current_year = datetime.now().year
    if appearance_date is not None:
        appearance_year = datetime.strptime(appearance_date, "%Y-%m-%d").year
    # Чтобы избежать деления на ноль (в случае, если текущий год вдруг окажется 2013)
    if current_year == 2013:
        appearance_weight = 100
    else:
        appearance_weight = ((current_year - appearance_year) / (current_year - 2013)) * 100
    
    if appearance_date is None:
        weight_number_of_items = weight_of_orders + price_weight + volatility_percent
    else:
        weight_number_of_items = weight_of_orders + price_weight + volatility_percent + appearance_weight
        
    weight = 1+ ((weight_number_of_items - 5) * 9 / 495)
    print(f"orders: {weight_of_orders}, price: {price_weight}, volatility: {volatility_percent}, date: {appearance_weight}")
    print(f"Вес до нормализации{weight_number_of_items}")
    print(f"Вес скина {skin}: {weight}")
    return weight

if __name__ == '__main__':
    with open("/home/pustrace/programming/trade/steam/database/perfect.json" , "r", encoding="utf-8") as f:
        skins = json.load(f)
        
    for skin, data in skins.items():
        lowest_price = data["lowest_price"]
        median_price = data["median_price"]
        volume = data["volume"]
        appearance_date = data.get("appearance_date")
        average_trend_percent = data["average_trend_percent"]
        volatility_percent = data["volatility_percent"]
        approx_min = data["approx_min"]
        approx_max = data["approx_max"]
        order_info = data.get("order_info")
        order_info_87 = data.get("order_info_87")
        order_info_last = data["order_info_last"]
        
        if order_info is None:
            order_info = (order_info_87 * 3)
            
        if order_info_87 is None:
            order_info_87 = 1
        if volume * 10 > order_info:
            weight_number_of_items = calculate_weight_number_of_items(lowest_price,
                                                                      median_price,
                                                                      order_info_87,
                                                                      order_info_last,
                                                                      volatility_percent,
                                                                      appearance_date)
    
    