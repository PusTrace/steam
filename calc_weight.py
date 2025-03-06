import json
def calculate_weight_number_or_items(skin, lowest_price, median_price, volume, appearance_date, average_trend_percent, volatility_percent, approx_min, approx_max, order_info):


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
        
        if volume * 10 > order_info:
        
        
    
    