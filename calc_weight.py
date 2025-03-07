import json
import math
from datetime import datetime

def calculate_weight_number_of_items(lowest_price,
                                    median_price,
                                    order_info_87,
                                    order_info_last,
                                    volatility_percent,
                                    appearance_date):
    orders = (order_info_last - order_info_87) / order_info_last
    weight_of_orders = max(orders*100, min(1, 100))
    price = median_price if median_price is not None else lowest_price
    # Коэффициент масштабирования для обратной экспоненты (можно подбирать эмпирически)
    scale = 300.0
    price_weight = math.exp(-price / scale) * 100
    
    current_year = datetime.now().year
    if appearance_date is None:
        if volatility_percent is None:
            weight_number_of_items = weight_of_orders + price_weight
        else:
            weight_number_of_items = weight_of_orders + price_weight + volatility_percent
    else:
        appearance_year = datetime.strptime(appearance_date, "%Y-%m-%d").year
        if current_year == 2013:
            appearance_weight = 100
        else:
            appearance_weight = ((current_year - appearance_year) / (current_year - 2013)) * 100
        if volatility_percent is None:
            weight_number_of_items = weight_of_orders + price_weight + appearance_weight 
        else:
            weight_number_of_items = weight_of_orders + price_weight + volatility_percent + appearance_weight 
    
        
    weight = 1+ ((weight_number_of_items - 5) * 9 / 495)
    print(f"orders: {weight_of_orders}, price: {price_weight}, volatility: {volatility_percent}")
    print(f"Вес до нормализации: {weight_number_of_items}")
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
        order_info_first = data.get("order_info_first")
        if order_info_87 is None:
            order_info_87 = 1
        if order_info_first is None:
            order_info_first = 1  
        if order_info_87 < volume * 3:
            weight_number_of_items = calculate_weight_number_of_items(lowest_price,
                                                                      median_price,
                                                                      order_info_87,
                                                                      order_info_last,
                                                                      volatility_percent,
                                                                      appearance_date)
    
    