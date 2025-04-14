import json

def filter_factory_new_skins(json_data, min_price=100, max_price=1000):
    factory_new_skins = {}
    
    for skin, details in json_data.items():
        if "Battle-Scarred" in skin and "lowest_price" in details and details["lowest_price"]:
            # Убираем ненужные символы и конвертируем цену в число
            price = float(details["lowest_price"].replace("₸", "").replace(" ", "").replace(",", "."))
            
            if min_price <= price <= max_price:
                factory_new_skins[skin] = details
    
    return factory_new_skins

with open('/home/pustrace/programming/steam_parser/filters/database.json', 'r', encoding='utf-8') as f:
    skins_data = json.load(f)

filtered_skins_factory = filter_factory_new_skins(skins_data)


with open('filtered_skins_batle.json', 'w', encoding='utf-8') as f:
    json.dump(filtered_skins_factory, f, ensure_ascii=False, indent=4)
