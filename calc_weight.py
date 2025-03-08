import json
import math
from datetime import datetime
import sys
import os
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
from utils.utils import save_data

def calculate_weight_number_of_items(lowest_price,
                                    median_price,
                                    volume,
                                    order_info_87,
                                    volatility_percent,
                                    appearance_date):
    if order_info_87 is None:
        order_info_87 = 1
    orders = (volume / order_info_87)
    weight_of_orders = max(orders, min(0.001, 100))
    price = median_price if median_price is not None else lowest_price
    scale = 300.0
    price_weight = math.exp(-price / scale) * 100
    weight_number_of_items = weight_of_orders + price_weight
    weight_of_items = weight_of_orders*1.5
    k = 2
    l = 1
    
    current_year = datetime.now().year
    if appearance_date is not None:
        appearance_year = datetime.strptime(appearance_date, "%Y-%m-%d").year
        if current_year == 2013:
            appearance_weight = 100
        else:
            appearance_weight = ((current_year - appearance_year) / (current_year - 2013)) * 100
        weight_number_of_items += appearance_weight
        weight_of_items += appearance_weight
        k += 1
        l += 1
    
    if volatility_percent is not None:
        weight_number_of_items += volatility_percent
        weight_of_items += volatility_percent
        k += 1
        l += 1
    weight = 1+ ((weight_number_of_items - k) * 9 / (k*100-k))
    return weight, weight_of_items

if __name__ == '__main__':
    with open("/home/pustrace/programming/trade/steam/database/perfect.json" , "r", encoding="utf-8") as f:
        skins = json.load(f)
        
    for skin, data in skins.items():
        lowest_price = data["lowest_price"]
        median_price = data["median_price"]
        volume = data.get("volume")
        appearance_date = data.get("appearance_date")
        average_trend_percent = data["average_trend_percent"]
        volatility_percent = data["volatility_percent"]
        approx_min = data["approx_min"]
        approx_max = data["approx_max"]
        order_info = data.get("order_info")
        order_info_87 = data.get("order_info_87")
        order_info_last = data["order_info_last"]
        order_info_first = data.get("order_info_first")
        weight_number_of_items, weight_of_items = calculate_weight_number_of_items(lowest_price,
                                                                    median_price,
                                                                    volume,
                                                                    order_info_87,
                                                                    volatility_percent,
                                                                    appearance_date)
        skins[skin] = {"weight_number_of_items": weight_number_of_items, "weight_of_items": weight_of_items}
        save_data(skins, "/home/pustrace/programming/trade/steam/database/perfect.json")
    
    