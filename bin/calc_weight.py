import math
from datetime import datetime

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
    