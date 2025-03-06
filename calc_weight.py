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
    # Предполагается, что appearance_date имеет формат "YYYY-MM-DD"
    appearance_year = datetime.strptime(appearance_date, "%Y-%m-%d").year
    # Чтобы избежать деления на ноль (в случае, если текущий год вдруг окажется 2013)
    if current_year == 2013:
        appearance_weight = 100
    else:
        appearance_weight = ((current_year - appearance_year) / (current_year - 2013)) * 100
    
    weight_number_of_items = weight_of_orders*0.5 + price_weight*0.5 + volatility_percent*0.5 + appearance_weight*0.5
    return weight_number_of_items

if __name__ == '__main__':
    with open("/home/pustrace/programming/trade/steam/database/perfect.json" , "r", encoding="utf-8") as f:
        skins = json.load(f)
        
    for skin, data in skins.items():
        lowest_price = data["lowest_price"]
        median_price = data["median_price"]
        volume = data["volume"]
        appearance_date = data["appearance_date"]
        average_trend_percent = data["average_trend_percent"]
        volatility_percent = data["volatility_percent"]
        approx_min = data["approx_min"]
        approx_max = data["approx_max"]
        order_info = data["order_info"]
        order_info_87 = data["order_info_87"]
        order_info_last = data["order_info_last"]
        
        if order_info is None:
            order_info = (order_info_87 * 3)
        if volume * 10 > order_info:
            weight_number_of_items = calculate_weight_number_of_items(skin,
                                                                      lowest_price,
                                                                      median_price,
                                                                      order_info_87,
                                                                      order_info_last,
                                                                      volatility_percent,
                                                                      appearance_date)
        
    
    